from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date, datetime
import uuid
import re
from pydantic import BaseModel
from typing import List, Optional, Literal
from app.core.dependencies import get_current_user, require_same_organization, get_permissions, PermissionChecker
from app.models.task import Task
from app.models.company import Company
from app.models.compliance_rule import ComplianceRule
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.team import Team
from app.models.task_comment import TaskComment
from app.services.notifications import create_notification
from app.schemas.task import TaskResponse, TaskDetailResponse, TaskUpdate, TaskAssignmentUpdate, CompanyMinResponse, RuleMinResponse, UserMinResponse, AuditLogMinResponse, TaskCommentCreate, TaskCommentResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskReassignRequest(BaseModel):
    assigned_user_id: uuid.UUID

async def _task_for_user(task_id: uuid.UUID, user: User) -> Task:
    task = await require_same_organization(await Task.get(task_id), user)
    if _work_role(user) in {"executive", "intern", "staff"} and task.assigned_to != user.id:
        raise HTTPException(status_code=404, detail="Resource not found")
    # Partners receive only work already approved by the Team Lead (and its
    # terminal closed state). This applies to detail routes as well as lists.
    if _work_role(user) == "partner" and task.status not in {"approved", "closed"}:
        raise HTTPException(status_code=404, detail="Resource not found")
    return task

async def _tenant_user(user_id: uuid.UUID | None, organization_id: uuid.UUID) -> User | None:
    if not user_id:
        return None
    user = await User.get(user_id)
    return user if user and user.organization_id == organization_id else None

async def _tenant_company(company_id: uuid.UUID, organization_id: uuid.UUID) -> Company | None:
    company = await Company.get(company_id)
    return company if company and company.organization_id == organization_id else None

def _work_role(user: User) -> str:
    return (user.designation or user.role or "").lower().replace(" ", "_")

async def _validate_assignment_authority(user: User, team: Team) -> None:
    role = _work_role(user)
    if role in {"executive", "intern", "staff"}:
        raise HTTPException(status_code=403, detail="Executives cannot assign tasks")
    if "can_assign_tasks" not in await get_permissions(user):
        raise HTTPException(status_code=403, detail="Missing required permission")
    if role == "team_lead" and team.id not in user.team_ids and user.id not in team.member_ids:
        raise HTTPException(status_code=403, detail="Team Leads can assign work only within their team")

@router.get("/assignment-options")
async def task_assignment_options(current_user: User = Depends(get_current_user)):
    """Tenant-scoped options used by the assignment drawer; no cross-firm users leak."""
    users = await User.find({"organization_id": current_user.organization_id, "is_active": True}).sort("full_name").to_list()
    teams = await Team.find({"organization_id": current_user.organization_id}).sort("name").to_list()
    return {
        "users": [UserMinResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role).model_dump() | {"designation": user.designation, "team_ids": user.team_ids} for user in users],
        "teams": [{"id": team.id, "name": team.name, "member_ids": team.member_ids} for team in teams],
    }

@router.put("/{task_id}/assignment")
async def assign_task(
    task_id: uuid.UUID,
    assignment: TaskAssignmentUpdate,
    current_user: User = Depends(get_current_user),
):
    task = await _task_for_user(task_id, current_user)

    team = await Team.get(assignment.assigned_team_id)
    if not team or team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=400, detail="Assigned team must belong to this organization")
    await _validate_assignment_authority(current_user, team)
    ids = [assignment.assigned_user_id, assignment.reviewer_id, assignment.approver_id]
    users = await User.find({"_id": {"$in": ids}, "organization_id": current_user.organization_id, "is_active": True}).to_list()
    if len(users) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Assigned users must be active members of this organization")
    executive = next(user for user in users if user.id == assignment.assigned_user_id)
    if executive.id not in team.member_ids and team.id not in executive.team_ids:
        raise HTTPException(status_code=400, detail="Assigned executive must belong to the selected team")
    previous = {field: str(getattr(task, field)) if getattr(task, field) else None for field in assignment.model_dump()}
    for field, value in assignment.model_dump().items():
        setattr(task, field, value)
    # Legacy task fields remain synchronized with the new lifecycle fields.
    task.assigned_team = assignment.assigned_team_id
    task.assigned_user = assignment.assigned_user_id
    task.assigned_to = assignment.assigned_user_id
    task.reviewer = assignment.reviewer_id
    task.approver = assignment.approver_id
    if task.status == "pending":
        task.current_stage = "executive"
    task.updated_at = datetime.utcnow()
    await task.save()
    await AuditLog(user_id=current_user.id, organization_id=current_user.organization_id,
                   action="task_assignment_updated", entity_type="task", entity_id=task.id,
                   action_metadata={"old": previous, "new": assignment.model_dump(mode="json")}).insert()
    await create_notification(
        organization_id=current_user.organization_id, user_id=assignment.assigned_user_id, task_id=task.id,
        type="assignment", title="New task assigned", message=f"You have been assigned: {task.title}",
        dedupe_key=f"task:{task.id}:assignment:{assignment.assigned_user_id}",
    )
    return {"id": str(task.id), "status": task.status}

async def _transition(task_id: uuid.UUID, user: User, target: str, permission: str | None, action: str):
    task = await _task_for_user(task_id, user)
    if permission and permission not in await get_permissions(user):
        raise HTTPException(status_code=403, detail="Missing required permission")
    old_status = task.status
    task.status = target
    task.updated_at = datetime.utcnow()
    await task.save()
    await AuditLog(user_id=user.id, organization_id=user.organization_id, action=action,
                   entity_type="task", entity_id=task.id,
                   action_metadata={"old_status": old_status, "new_status": target}).insert()
    return {"id": str(task.id), "status": task.status}

@router.post("/{task_id}/submit-review")
async def submit_for_review(task_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=400, detail="Use the workflow transition endpoint")

@router.post("/{task_id}/review")
async def review_task(task_id: uuid.UUID, approve: bool = True, current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=400, detail="Use the workflow transition endpoint")

@router.post("/{task_id}/approve")
async def approve_task(task_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=400, detail="Use the workflow transition endpoint")

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    current_stage: Optional[str] = None,
    company_id: Optional[uuid.UUID] = None,
    assigned_to: Optional[uuid.UUID] = None,
    due_start: Optional[date] = None,
    due_end: Optional[date] = None,
    category: Optional[str] = None,  # cs, ca
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    query = {"organization_id": current_user.organization_id}
    work_role = _work_role(current_user)
    if work_role in {"executive", "intern", "staff"}:
        # Executive dashboards must never expose another user's workload.
        query["assigned_to"] = current_user.id
    elif work_role == "partner":
        query["status"] = {"$in": ["approved", "closed"]}
    if status is not None and work_role != "partner":
        query["status"] = status
    if current_stage is not None:
        query["current_stage"] = current_stage
    if company_id is not None:
        query["company_id"] = company_id
    if assigned_to is not None and work_role not in {"executive", "intern", "staff"}:
        query["assigned_to"] = assigned_to
    if category is not None:
        query["category"] = category
    if due_start is not None:
        query["due_date"] = query.get("due_date", {})
        query["due_date"]["$gte"] = due_start
    if due_end is not None:
        query["due_date"] = query.get("due_date", {})
        query["due_date"]["$lte"] = due_end
        
    if "due_date" in query and not query["due_date"]:
        del query["due_date"]

    tasks = await Task.find(query).sort("due_date").skip(offset).limit(limit).to_list()
    
    response_tasks = []
    company_cache = {}
    user_cache = {}
    
    for t in tasks:
        company_min = None
        if t.company_id not in company_cache:
            c = await _tenant_company(t.company_id, current_user.organization_id)
            if c:
                company_cache[t.company_id] = CompanyMinResponse(
                    id=c.id, name=c.name, cin=c.cin, company_type=c.company_type
                )
            else:
                company_cache[t.company_id] = None
        company_min = company_cache[t.company_id]
        
        assigned_user = None
        if t.assigned_to:
            if t.assigned_to not in user_cache:
                u = await _tenant_user(t.assigned_to, current_user.organization_id)
                if u:
                    user_cache[t.assigned_to] = UserMinResponse(
                        id=u.id, email=u.email, full_name=u.full_name, role=u.role
                    )
                else:
                    user_cache[t.assigned_to] = None
            assigned_user = user_cache[t.assigned_to]
            
        response_tasks.append(
            TaskResponse(
                id=t.id,
                company_id=t.company_id,
                rule_id=t.rule_id,
                title=t.title,
                description=t.description,
                due_date=t.due_date,
                status=t.status,
                current_stage=t.current_stage,
                assigned_to=t.assigned_to,
                completed_by=t.completed_by,
                completed_at=t.completed_at,
                reference_doc=t.reference_doc,
                notes=t.notes,
                category=t.category,
                created_at=t.created_at,
                updated_at=t.updated_at,
                company=company_min,
                assigned_user=assigned_user
            )
        )
    return response_tasks

async def _workload_teams_for_user(user: User) -> list[Team]:
    role = _work_role(user)
    if role == "partner":
        return await Team.find({"organization_id": user.organization_id}).sort("name").to_list()
    if role != "manager":
        raise HTTPException(status_code=403, detail="Manager or Partner access required")
    return await Team.find({"organization_id": user.organization_id, "manager_id": user.id}).sort("name").to_list()

@router.get("/workload")
async def team_workload(current_user: User = Depends(get_current_user)):
    teams = await _workload_teams_for_user(current_user)
    team_ids = [team.id for team in teams]
    if not team_ids:
        return {"teams": []}
    users = await User.find({"organization_id": current_user.organization_id, "is_active": True}).to_list()
    users_by_id = {user.id: user for user in users}
    tasks = await Task.find({"organization_id": current_user.organization_id, "$or": [
        {"assigned_team_id": {"$in": team_ids}}, {"assigned_team": {"$in": team_ids}}
    ]}).to_list()
    today = date.today()
    payload = []
    for team in teams:
        member_ids = list(dict.fromkeys([*team.member_ids, *([team.manager_id] if team.manager_id else [])]))
        team_tasks = [task for task in tasks if (task.assigned_team_id or task.assigned_team) == team.id]
        members = []
        for member_id in member_ids:
            member = users_by_id.get(member_id)
            if not member:
                continue
            active = [task for task in team_tasks if task.assigned_to == member_id and task.status != "closed"]
            members.append({"id": str(member.id), "name": member.full_name or member.email, "email": member.email,
                "pending": sum(task.status in {"pending", "returned_with_comments"} for task in active),
                "in_progress": sum(task.status == "in_progress" for task in active),
                "overdue": sum(task.due_date < today for task in active), "total_active": len(active),
                "tasks": [{"id": str(task.id), "title": task.title, "status": task.status, "due_date": task.due_date.isoformat()} for task in active]})
        payload.append({"id": str(team.id), "name": team.name, "members": members})
    return {"teams": payload}

@router.post("/{task_id}/reassign")
async def reassign_task(task_id: uuid.UUID, request: TaskReassignRequest, current_user: User = Depends(get_current_user)):
    task = await require_same_organization(await Task.get(task_id), current_user)
    teams = await _workload_teams_for_user(current_user)
    allowed_team_ids = {team.id for team in teams}
    task_team_id = task.assigned_team_id or task.assigned_team
    if task_team_id not in allowed_team_ids:
        raise HTTPException(status_code=403, detail="You can only reassign tasks in teams you oversee")
    team = next(team for team in teams if team.id == task_team_id)
    recipient = await _tenant_user(request.assigned_user_id, current_user.organization_id)
    if not recipient or (recipient.id not in team.member_ids and recipient.id != team.manager_id):
        raise HTTPException(status_code=400, detail="New assignee must be an active member of this team")
    old_assignee = task.assigned_to
    if old_assignee == recipient.id:
        return {"id": str(task.id), "assigned_to": str(recipient.id)}
    task.assigned_to = task.assigned_user = task.assigned_user_id = recipient.id
    task.updated_at = datetime.utcnow()
    await task.save()
    old_user = await _tenant_user(old_assignee, current_user.organization_id)
    await AuditLog(user_id=current_user.id, organization_id=current_user.organization_id, action="task_reassigned",
                   entity_type="task", entity_id=task.id,
                   action_metadata={"old_assignee": (old_user.full_name or old_user.email) if old_user else "Unassigned",
                                    "new_assignee": recipient.full_name or recipient.email, "team": team.name}).insert()
    await create_notification(organization_id=current_user.organization_id, user_id=recipient.id, task_id=task.id,
                              type="assignment", title="Task reassigned to you", message=f"You have been assigned: {task.title}",
                              dedupe_key=f"task:{task.id}:reassignment:{recipient.id}:{task.updated_at.isoformat()}")
    return {"id": str(task.id), "assigned_to": str(recipient.id)}

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    task = await _task_for_user(task_id, current_user)
        
    company_doc = await _tenant_company(task.company_id, current_user.organization_id)
    company_min = CompanyMinResponse(
        id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
    ) if company_doc else None
    
    rule_doc = await ComplianceRule.get(task.rule_id) if task.rule_id else None
    if rule_doc and rule_doc.organization_id not in {None, current_user.organization_id}:
        rule_doc = None
    rule_min = RuleMinResponse(
        id=rule_doc.id, name=rule_doc.name, form_number=rule_doc.form_number
    ) if rule_doc else None
    
    assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
    assignee_min = UserMinResponse(
        id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
    ) if assignee_doc else None
    
    completed_doc = await _tenant_user(task.completed_by, current_user.organization_id)
    completed_min = UserMinResponse(
        id=completed_doc.id, email=completed_doc.email, full_name=completed_doc.full_name, role=completed_doc.role
    ) if completed_doc else None
    
    logs = await AuditLog.find({
        "organization_id": current_user.organization_id, "entity_type": "task", "entity_id": task_id
    }).sort("-created_at").limit(5).to_list()
    
    response_logs = []
    user_cache = {}
    for log in logs:
        log_user = None
        if log.user_id:
            if log.user_id not in user_cache:
                u = await _tenant_user(log.user_id, current_user.organization_id)
                if u:
                    user_cache[log.user_id] = UserMinResponse(
                        id=u.id, email=u.email, full_name=u.full_name, role=u.role
                    )
                else:
                    user_cache[log.user_id] = None
            log_user = user_cache[log.user_id]
            
        response_logs.append(
            AuditLogMinResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                action_metadata=log.action_metadata,
                created_at=log.created_at,
                user=log_user
            )
        )
        
    # Fetch comments
    comments_list = await TaskComment.find({"task_id": task_id}).sort("created_at").to_list()
    response_comments = [
        TaskCommentResponse(
            id=c.id,
            task_id=c.task_id,
            user_id=c.user_id,
            user_name=c.user_name,
            content=c.content,
            created_at=c.created_at
        ) for c in comments_list
    ]
        
    task_detail = TaskDetailResponse(
        id=task.id,
        company_id=task.company_id,
        rule_id=task.rule_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        status=task.status,
        current_stage=task.current_stage,
        assigned_to=task.assigned_to,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        reference_doc=task.reference_doc,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        company=company_min,
        rule=rule_min,
        assigned_user=assignee_min,
        completed_user=completed_min,
        audit_logs=response_logs,
        comments=response_comments
    )
    return task_detail

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user)
):
    task = await _task_for_user(task_id, current_user)

    if "status" in task_in.model_fields_set or "current_stage" in task_in.model_fields_set:
        raise HTTPException(status_code=400, detail="Workflow status can only be changed through the task transition endpoint")

    permissions = await get_permissions(current_user)
    if any(key in task_in.model_fields_set for key in ("assigned_to", "assigned_team", "assigned_user")) and "can_assign_tasks" not in permissions:
        raise HTTPException(status_code=403, detail="Missing required permission")
    if "reviewer" in task_in.model_fields_set and "can_review_tasks" not in permissions:
        raise HTTPException(status_code=403, detail="Missing required permission")
    if "approver" in task_in.model_fields_set and "can_approve_tasks" not in permissions:
        raise HTTPException(status_code=403, detail="Missing required permission")
        
    update_data = task_in.model_dump(exclude_unset=True)
    
    assignee_changed = False
    old_assignee_id = task.assigned_to
    new_assignee_id = update_data.get("assigned_to", old_assignee_id)
    if "assigned_to" in update_data and old_assignee_id != new_assignee_id:
        assignee_changed = True
        
    status_changed = False
    old_status = task.status
    new_status = update_data.get("status", old_status)
    if "status" in update_data and old_status != new_status:
        status_changed = True

        # Keep completion metadata consistent for direct status changes.
        if new_status == "completed":
            task.completed_by = current_user.id
            task.completed_at = datetime.utcnow()
        elif old_status == "completed":
            task.completed_by = None
            task.completed_at = None
        task.status_manually_set = True
        
    for field, value in update_data.items():
        setattr(task, field, value)
        
    task.updated_at = datetime.utcnow()
    await task.save()
    
    if assignee_changed:
        old_name = "Unassigned"
        new_name = "Unassigned"
        if old_assignee_id:
            old_usr = await _tenant_user(old_assignee_id, current_user.organization_id)
            if old_usr: old_name = old_usr.full_name or old_usr.email
        if new_assignee_id:
            new_usr = await _tenant_user(new_assignee_id, current_user.organization_id)
            if new_usr: new_name = new_usr.full_name or new_usr.email
            
        audit = AuditLog(
            user_id=current_user.id, organization_id=current_user.organization_id,
            action="task_reassigned",
            entity_type="task",
            entity_id=task.id,
            action_metadata={"old_assignee": old_name, "new_assignee": new_name}
        )
        await audit.insert()
    elif status_changed:
        audit = AuditLog(
            user_id=current_user.id, organization_id=current_user.organization_id,
            action="task_status_updated",
            entity_type="task",
            entity_id=task.id,
            action_metadata={"old_status": old_status, "new_status": new_status}
        )
        await audit.insert()
    else:
        audit = AuditLog(
            user_id=current_user.id, organization_id=current_user.organization_id,
            action="task_updated",
            entity_type="task",
            entity_id=task.id,
            action_metadata={"fields_updated": list(update_data.keys())}
        )
        await audit.insert()

    if assignee_changed:
        await create_notification(
            organization_id=current_user.organization_id, user_id=new_assignee_id, task_id=task.id,
            type="assignment", title="Task assigned to you", message=f"You have been assigned: {task.title}",
            dedupe_key=f"task:{task.id}:assignment:{new_assignee_id}",
        )
        
    company_doc = await _tenant_company(task.company_id, current_user.organization_id)
    company_min = CompanyMinResponse(
        id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
    ) if company_doc else None
    
    assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
    assignee_min = UserMinResponse(
        id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
    ) if assignee_doc else None
    
    return TaskResponse(
        id=task.id,
        company_id=task.company_id,
        rule_id=task.rule_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        status=task.status,
        current_stage=task.current_stage,
        assigned_to=task.assigned_to,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        reference_doc=task.reference_doc,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        company=company_min,
        assigned_user=assignee_min
    )

@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    raise HTTPException(status_code=400, detail="Use the workflow transition endpoint to complete executive work")
    task = await _task_for_user(task_id, current_user)
        
    if task.status == "completed":
        company_doc = await _tenant_company(task.company_id, current_user.organization_id)
        company_min = CompanyMinResponse(
            id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
        ) if company_doc else None
        assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
        assignee_min = UserMinResponse(
            id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
        ) if assignee_doc else None
        return TaskResponse(
            id=task.id,
            company_id=task.company_id,
            rule_id=task.rule_id,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            status=task.status,
            current_stage=task.current_stage,
            assigned_to=task.assigned_to,
            completed_by=task.completed_by,
            completed_at=task.completed_at,
            reference_doc=task.reference_doc,
            notes=task.notes,
            created_at=task.created_at,
            updated_at=task.updated_at,
            company=company_min,
            assigned_user=assignee_min
        )
        
    old_status = task.status
    task.status = "completed"
    task.status_manually_set = True
    task.completed_by = current_user.id
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    await task.save()
    
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="task_completed",
        entity_type="task",
        entity_id=task.id,
        action_metadata={"old_status": old_status, "completed_by_name": current_user.full_name or current_user.email}
    )
    await audit.insert()

    company_doc = await _tenant_company(task.company_id, current_user.organization_id)
    company_min = CompanyMinResponse(
        id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
    ) if company_doc else None
    
    assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
    assignee_min = UserMinResponse(
        id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
    ) if assignee_doc else None
    
    return TaskResponse(
        id=task.id,
        company_id=task.company_id,
        rule_id=task.rule_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        status=task.status,
        current_stage=task.current_stage,
        assigned_to=task.assigned_to,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        reference_doc=task.reference_doc,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        company=company_min,
        assigned_user=assignee_min
    )

@router.post("/{task_id}/reopen", response_model=TaskResponse)
async def reopen_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    raise HTTPException(status_code=400, detail="Closed work cannot be reopened; return it with comments during review")
    task = await _task_for_user(task_id, current_user)
        
    if task.status != "completed":
        company_doc = await _tenant_company(task.company_id, current_user.organization_id)
        company_min = CompanyMinResponse(
            id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
        ) if company_doc else None
        assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
        assignee_min = UserMinResponse(
            id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
        ) if assignee_doc else None
        return TaskResponse(
            id=task.id,
            company_id=task.company_id,
            rule_id=task.rule_id,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            status=task.status,
            current_stage=task.current_stage,
            assigned_to=task.assigned_to,
            completed_by=task.completed_by,
            completed_at=task.completed_at,
            reference_doc=task.reference_doc,
            notes=task.notes,
            created_at=task.created_at,
            updated_at=task.updated_at,
            company=company_min,
            assigned_user=assignee_min
        )
        
    task.status = "upcoming"
    task.status_manually_set = True
    task.completed_by = None
    task.completed_at = None
    task.updated_at = datetime.utcnow()
    await task.save()
    
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="task_reopened",
        entity_type="task",
        entity_id=task.id,
        action_metadata={"reopened_by_name": current_user.full_name or current_user.email}
    )
    await audit.insert()
    
    company_doc = await _tenant_company(task.company_id, current_user.organization_id)
    company_min = CompanyMinResponse(
        id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
    ) if company_doc else None
    
    assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
    assignee_min = UserMinResponse(
        id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
    ) if assignee_doc else None
    
    return TaskResponse(
        id=task.id,
        company_id=task.company_id,
        rule_id=task.rule_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        status=task.status,
        current_stage=task.current_stage,
        assigned_to=task.assigned_to,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        reference_doc=task.reference_doc,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        company=company_min,
        assigned_user=assignee_min
    )

@router.delete("/{task_id}", response_model=TaskResponse)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(PermissionChecker("can_manage_settings"))
):
    task = await _task_for_user(task_id, current_user)
        
    await task.delete()
    
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="task_deleted",
        entity_type="task",
        entity_id=task_id,
        action_metadata={"task_title": task.title}
    )
    await audit.insert()
    
    company_doc = await _tenant_company(task.company_id, current_user.organization_id)
    company_min = CompanyMinResponse(
        id=company_doc.id, name=company_doc.name, cin=company_doc.cin, company_type=company_doc.company_type
    ) if company_doc else None
    
    assignee_doc = await _tenant_user(task.assigned_to, current_user.organization_id)
    assignee_min = UserMinResponse(
        id=assignee_doc.id, email=assignee_doc.email, full_name=assignee_doc.full_name, role=assignee_doc.role
    ) if assignee_doc else None
    
    return TaskResponse(
        id=task.id,
        company_id=task.company_id,
        rule_id=task.rule_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        status=task.status,
        current_stage=task.current_stage,
        assigned_to=task.assigned_to,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        reference_doc=task.reference_doc,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        company=company_min,
        assigned_user=assignee_min
    )

class WorkflowTransitionRequest(BaseModel):
    action: Literal["start", "complete", "submit", "approve", "close", "return"]
    comment: Optional[str] = None

@router.post("/{task_id}/transition")
async def transition_task_workflow(
    task_id: uuid.UUID,
    req: WorkflowTransitionRequest,
    current_user: User = Depends(get_current_user)
):
    task = await _task_for_user(task_id, current_user)
    work_role = _work_role(current_user)
    old_status = task.status
    old_stage = task.current_stage or "executive"
    permissions = await get_permissions(current_user)
    is_executive = current_user.id == task.assigned_to or (not task.assigned_to and work_role in {"executive", "intern", "staff", "ca"})
    is_team_lead = work_role in {"team_lead", "admin"} or current_user.id == task.reviewer_id
    is_partner = work_role in {"partner", "admin"} or "can_approve_tasks" in permissions

    if task.status == "pending" and req.action == "start" and is_executive:
        task.status, task.current_stage = "in_progress", "executive"
    elif task.status == "returned_with_comments" and req.action == "start" and is_executive:
        task.status, task.current_stage = "in_progress", "executive"
    elif task.status == "in_progress" and req.action == "complete" and is_executive:
        task.status, task.current_stage = "completed_by_executive", "executive"
        task.completed_by, task.completed_at = current_user.id, datetime.utcnow()
    elif task.status == "completed_by_executive" and req.action == "submit" and is_executive:
        task.status, task.current_stage = "waiting_for_review", "team_lead"
    elif task.status == "waiting_for_review" and req.action == "approve" and is_team_lead:
        task.status, task.current_stage = "approved", "partner"
    elif task.status == "waiting_for_review" and req.action == "return" and is_team_lead:
        if not req.comment or not req.comment.strip():
            raise HTTPException(status_code=400, detail="Comments are required when returning work")
        task.status, task.current_stage = "returned_with_comments", "executive"
        task.completed_by, task.completed_at = None, None
    elif task.status == "approved" and req.action == "close" and is_partner:
        task.status, task.current_stage = "closed", "closed"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid '{req.action}' action for task status '{task.status}'")
        
    task.updated_at = datetime.utcnow()
    await task.save()
    
    comment_id = None
    if req.comment:
        comment = TaskComment(
            task_id=task.id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            content=req.comment
        )
        await comment.insert()
        comment_id = comment.id
        
    audit = AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action=f"task_workflow_{req.action}",
        entity_type="task",
        entity_id=task.id,
        action_metadata={
            "old_status": old_status,
            "new_status": task.status,
            "old_stage": old_stage,
            "new_stage": task.current_stage,
            "comment": req.comment,
            "comment_id": str(comment_id) if comment_id else None
        }
    )
    await audit.insert()

    if task.status == "completed_by_executive":
        await create_notification(
            organization_id=current_user.organization_id, user_id=task.reviewer_id or task.reviewer, task_id=task.id,
            type="completion", title="Task ready for review", message=f"{task.title} was completed and is ready for your review.",
            dedupe_key=f"task:{task.id}:completion-review",
        )
    elif task.status == "approved":
        await create_notification(
            organization_id=current_user.organization_id, user_id=task.assigned_to, task_id=task.id,
            type="approval", title="Task approved", message=f"Your work on {task.title} has been approved.",
            dedupe_key=f"task:{task.id}:approved:{task.assigned_to}",
        )
    
    return {
        "id": str(task.id),
        "status": task.status,
        "current_stage": task.current_stage
    }

@router.get("/{task_id}/comments", response_model=List[TaskCommentResponse])
async def get_task_comments(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    await _task_for_user(task_id, current_user)
    comments = await TaskComment.find({"task_id": task_id}).sort("created_at").to_list()
    return comments

@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
async def create_task_comment(
    task_id: uuid.UUID,
    comment_in: TaskCommentCreate,
    current_user: User = Depends(get_current_user)
):
    task = await _task_for_user(task_id, current_user)
    comment = TaskComment(
        task_id=task.id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.email,
        content=comment_in.content
    )
    await comment.insert()

    # Mentions resolve against tenant-local full-name words and email local parts.
    mentioned = {value.lower() for value in re.findall(r"@([A-Za-z0-9._-]+)", comment.content)}
    if mentioned:
        users = await User.find({"organization_id": current_user.organization_id, "is_active": True}).to_list()
        for user in users:
            aliases = {(user.email or "").split("@")[0].lower()}
            aliases.update((user.full_name or "").lower().split())
            aliases.add((user.full_name or "").lower().replace(" ", "."))
            if user.id != current_user.id and mentioned.intersection(aliases):
                await create_notification(
                    organization_id=current_user.organization_id, user_id=user.id, task_id=task.id,
                    type="mentions", title="You were mentioned", message=f"{current_user.full_name or current_user.email} mentioned you on {task.title}.",
                    dedupe_key=f"comment:{comment.id}:mention:{user.id}",
                )
    
    # Log comment addition
    audit = AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="task_comment_added",
        entity_type="task",
        entity_id=task.id,
        action_metadata={"comment_id": str(comment.id)}
    )
    await audit.insert()
    
    return comment
