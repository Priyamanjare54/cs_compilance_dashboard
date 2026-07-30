from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from typing import List, Optional
from app.core.dependencies import get_current_user, require_same_organization
from app.models.company import Company
from app.models.task import Task
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.compliance_rule import ComplianceRule
from app.models.team import Team
from app.models.compliance_calendar import ComplianceCalendar
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyDetailResponse, TasksSummary, ClientAssignmentUpdate
from app.schemas.task import TaskResponse, CompanyMinResponse, UserMinResponse, AuditLogMinResponse
from app.schemas.company_360 import Company360ViewResponse, Company360Task, CompanyDocument, ClientAssignmentSummary
from app.schemas.compliance_calendar import ComplianceCalendarResponse
from app.services.rule_engine import run_rule_engine_for_company
import re

router = APIRouter(prefix="/companies", tags=["companies"])
clients_router = APIRouter(prefix="/clients", tags=["clients"])

DEFAULT_TEAM_PREFERENCE = {
    "private_limited": ["roc", "core", "compliance"],
    "public_limited": ["roc", "core", "compliance"],
    "opc": ["roc", "core", "compliance"],
    "llp": ["llp", "compliance", "roc"],
    "partnership": ["partnership", "compliance", "roc"],
    "proprietorship": ["proprietorship", "tax", "compliance"],
    "individual": ["individual", "tax", "compliance"],
}

async def _find_default_team(company: Company, organization_id: uuid.UUID) -> Team | None:
    teams = await Team.find({"organization_id": organization_id}).to_list()
    if not teams:
        return None

    if company.assigned_team_id:
        assigned_team = await Team.get(company.assigned_team_id)
        if assigned_team and assigned_team.organization_id == organization_id:
            return assigned_team

    industry = (company.industry or "").strip().lower()
    if industry:
        for team in teams:
            if industry in (team.name or "").lower():
                return team

    preferred = DEFAULT_TEAM_PREFERENCE.get((company.company_type or "").lower(), ["compliance"])
    for keyword in preferred:
        for team in teams:
            if keyword in (team.name or "").lower():
                return team

    return teams[0]

async def _find_default_partner(organization_id: uuid.UUID) -> uuid.UUID | None:
    partners = await User.find({
        "organization_id": organization_id,
        "is_active": True,
        "$or": [{"role": "partner"}, {"designation": "partner"}],
    }).sort("full_name").to_list()
    return partners[0].id if partners else None

async def _find_default_manager(team: Team | None, organization_id: uuid.UUID) -> uuid.UUID | None:
    if team and team.manager_id:
        manager = await User.get(team.manager_id)
        if manager and manager.organization_id == organization_id and manager.is_active:
            return manager.id
    managers = await User.find({
        "organization_id": organization_id,
        "is_active": True,
        "$or": [{"role": "manager"}, {"designation": "manager"}],
    }).sort("full_name").to_list()
    return managers[0].id if managers else None

async def _get_team_by_id(team_id: uuid.UUID, organization_id: uuid.UUID) -> Team | None:
    if not team_id:
        return None
    team = await Team.get(team_id)
    return team if team and team.organization_id == organization_id else None

def _is_executive(user: User) -> bool:
    return (user.designation or user.role or "").lower().replace(" ", "_") in {"executive", "intern", "staff"}


async def _company_for_user(company_id: uuid.UUID, user: User) -> Company:
    if _is_executive(user):
        raise HTTPException(status_code=404, detail="Resource not found")
    return await require_same_organization(await Company.get(company_id), user)

async def _tenant_user(user_id: uuid.UUID | None, organization_id: uuid.UUID) -> User | None:
    if not user_id:
        return None
    user = await User.get(user_id)
    return user if user and user.organization_id == organization_id else None

async def _resolve_team_assignee(data: ClientAssignmentUpdate, organization_id: uuid.UUID) -> uuid.UUID:
    """Validate the allocation and derive the person who receives the team's tasks."""
    oversight_ids = [data.relationship_partner_id, data.manager_id]
    users = await User.find({"_id": {"$in": oversight_ids}, "organization_id": organization_id, "is_active": True}).to_list()
    if len(users) != len(set(oversight_ids)):
        raise HTTPException(status_code=400, detail="Assigned users must be active members of this organization")

    team = await Team.get(data.assigned_team_id)
    if not team or team.organization_id != organization_id:
        raise HTTPException(status_code=400, detail="Assigned team must belong to this organization")

    candidate_ids = list(dict.fromkeys(
        ([team.manager_id] if team.manager_id else []) + list(team.member_ids or [])
    ))
    members = await User.find({
        "_id": {"$in": candidate_ids},
        "organization_id": organization_id,
        "is_active": True,
    }).to_list() if candidate_ids else []
    active_member_ids = {member.id for member in members}
    assignee_id = next((candidate_id for candidate_id in candidate_ids if candidate_id in active_member_ids), None)
    if not assignee_id:
        raise HTTPException(status_code=400, detail="Assigned team must have at least one active member")
    return assignee_id


def _apply_assignment(company: Company, data: ClientAssignmentUpdate, assignee_id: uuid.UUID) -> None:
    company.relationship_partner_id = data.relationship_partner_id
    company.manager_id = data.manager_id
    company.assigned_team_id = data.assigned_team_id
    company.primary_executive_id = assignee_id
    # Preserve the existing assignment fields for older task/calendar screens.
    company.assigned_to = assignee_id
    company.assigned_team = data.assigned_team_id
    company.relationship_manager = data.manager_id


def _display_category(task: Task) -> str:
    """Translate existing CS/CA task categories into the Client 360 filters."""
    title = task.title.lower()
    if "gst" in title or "gstr" in title:
        return "GST"
    if any(term in title for term in ("tax", "itr", "tds")):
        return "Tax"
    if task.category == "cs" and any(term in title for term in ("mgt", "dir", "ben", "pas", "board", "resolution")):
        return "Secretarial"
    return "ROC" if task.category == "cs" else "Tax"


def _priority(task: Task) -> str:
    if task.status == "overdue":
        return "High"
    if task.status == "due_soon":
        return "Medium"
    return "Low"


@router.get("/{company_id}/360-view", response_model=Company360ViewResponse)
async def get_company_360_view(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    """Return all currently stored, company-scoped information in one request."""
    company = await _company_for_user(company_id, current_user)

    tasks = await Task.find({"company_id": company_id, "organization_id": current_user.organization_id}).sort("due_date").to_list()
    task_ids = [task.id for task in tasks]
    user_ids = {task.assigned_to for task in tasks if task.assigned_to}
    user_ids.update(user_id for user_id in (company.relationship_partner_id, company.manager_id, company.primary_executive_id) if user_id)
    users = [user for user in [await _tenant_user(user_id, current_user.organization_id) for user_id in user_ids] if user] if user_ids else []
    users_by_id = {user.id: user for user in users}

    def user_min(user_id: uuid.UUID | None):
        user = users_by_id.get(user_id) if user_id else None
        return UserMinResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role) if user else None

    counts = {"overdue": 0, "due_soon": 0, "upcoming": 0, "completed": 0, "total": 0}
    response_tasks = []
    documents = []
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
            counts["total"] += 1
        response_tasks.append(Company360Task(
            id=task.id, title=task.title, due_date=task.due_date, status=task.status,
            category=task.category, display_category=_display_category(task), priority=_priority(task),
            assigned_to=task.assigned_to, assigned_user=user_min(task.assigned_to),
        ))
        # reference_doc is the only existing, company-related file field.
        if task.reference_doc:
            documents.append(CompanyDocument(
                id=task.id, title=f"{task.title} reference document", category=_display_category(task),
                uploaded_at=task.updated_at, download_url=task.reference_doc,
            ))

    logs_query = {"organization_id": current_user.organization_id, "$or": [
        {"entity_type": "company", "entity_id": company_id},
        {"entity_type": "task", "entity_id": {"$in": task_ids}},
    ]}
    logs = await AuditLog.find(logs_query).sort("-created_at").limit(100).to_list()
    log_user_ids = {log.user_id for log in logs if log.user_id} - set(users_by_id)
    if log_user_ids:
        log_users = [user for user in [await _tenant_user(user_id, current_user.organization_id) for user_id in log_user_ids] if user]
        users_by_id.update({user.id: user for user in log_users})

    response_logs = [AuditLogMinResponse(
        id=log.id, user_id=log.user_id, action=log.action, entity_type=log.entity_type,
        entity_id=log.entity_id, action_metadata=log.action_metadata, created_at=log.created_at,
        user=user_min(log.user_id),
    ) for log in logs]

    calendar_items = await ComplianceCalendar.find({"organization_id": current_user.organization_id, "client_id": company.id}).sort("due_date").to_list()
    calendar_response = []
    for item in calendar_items:
        rule = await ComplianceRule.get(item.compliance_rule_id)
        if rule and rule.organization_id not in {None, current_user.organization_id}:
            rule = None
        calendar_response.append(ComplianceCalendarResponse(**item.model_dump(), rule_name=rule.name if rule else "Compliance rule"))

    team = await Team.get(company.assigned_team_id) if company.assigned_team_id else None
    return Company360ViewResponse(
        company=company, industry=None, tasks_summary=TasksSummary(**counts), tasks=response_tasks,
        documents=documents, contacts=[], audit_logs=response_logs,
        assignment=ClientAssignmentSummary(
            relationship_partner=user_min(company.relationship_partner_id),
            manager=user_min(company.manager_id),
            team_id=company.assigned_team_id,
            team_name=team.name if team and team.organization_id == current_user.organization_id else None,
            primary_executive=user_min(company.primary_executive_id),
        ),
        calendar=calendar_response,
    )

@clients_router.get("", response_model=List[CompanyResponse])
@router.get("", response_model=List[CompanyResponse])
async def get_companies(
    assigned_to: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    company_type: Optional[str] = None,
    client_type: Optional[str] = None,  # cs, ca, both
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve companies with optional filters:
    - **search**: Partial, case-insensitive match on company name, CIN, PAN, or GSTIN.
    - **company_type**: Filter by type.
    - **assigned_to**: Filter by assigned staff user ID.
    - **is_active**: Filter by active/inactive status.
    - **client_type**: Filter by CS or CA workspace mode.
    """
    if _is_executive(current_user):
        return []

    query = {"organization_id": current_user.organization_id}
    if assigned_to is not None:
        query["assigned_to"] = assigned_to
    if is_active is not None:
        query["is_active"] = is_active
    if company_type is not None:
        query["company_type"] = company_type
    if client_type is not None:
        if client_type == "cs":
            query["client_type"] = {"$in": ["cs", "both"]}
        elif client_type == "ca":
            query["client_type"] = {"$in": ["ca", "both"]}
        else:
            query["client_type"] = client_type

    if search is not None and search.strip():
        escaped = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"cin": {"$regex": escaped, "$options": "i"}},
            {"pan": {"$regex": escaped, "$options": "i"}},
            {"gstin": {"$regex": escaped, "$options": "i"}}
        ]

    companies = await Company.find(query).skip(offset).limit(limit).to_list()
    return companies

@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_user)
):
    if _is_executive(current_user):
        raise HTTPException(status_code=403, detail="Executives cannot manage companies")

    if company_in.cin:
        existing = await Company.find_one({"cin": company_in.cin, "organization_id": current_user.organization_id})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this CIN already exists."
            )
    elif company_in.pan:
        existing = await Company.find_one({"pan": company_in.pan, "organization_id": current_user.organization_id})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this PAN already exists."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either CIN or PAN must be provided."
        )

    company_data = company_in.model_dump(exclude_none=True)
    company = Company(**company_data, organization_id=current_user.organization_id)

    team = await _get_team_by_id(company.assigned_team_id, current_user.organization_id)
    if not team:
        team = await _find_default_team(company, current_user.organization_id)
        if team:
            company.assigned_team_id = team.id
            company.assigned_team = team.id

    if not company.relationship_partner_id:
        company.relationship_partner_id = await _find_default_partner(current_user.organization_id)
    if not company.manager_id:
        company.manager_id = await _find_default_manager(team, current_user.organization_id)

    if not company.assigned_team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not infer a default team assignment for this company. Please create a team first or provide an assigned team."
        )
    if not company.relationship_partner_id or not company.manager_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not infer a default partner or manager assignment. Please provide these fields explicitly."
        )

    assignment = ClientAssignmentUpdate(
        relationship_partner_id=company.relationship_partner_id,
        manager_id=company.manager_id,
        assigned_team_id=company.assigned_team_id,
    )
    assignee_id = await _resolve_team_assignee(assignment, current_user.organization_id)
    _apply_assignment(company, assignment, assignee_id)
    await company.insert()

    # Log audit: company created
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="company_created",
        entity_type="company",
        entity_id=company.id,
        action_metadata={"cin": company.cin, "pan": company.pan, "name": company.name, "company_type": company.company_type}
    )
    await audit.insert()

    # Run the rule engine to auto-generate tasks
    await run_rule_engine_for_company(None, company, user_id=current_user.id)

    return company

@clients_router.get("/{company_id}", response_model=CompanyDetailResponse)
@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company_detail(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    company = await _company_for_user(company_id, current_user)
        
    # Count tasks grouped by status for this company
    tasks = await Task.find({"company_id": company_id, "organization_id": current_user.organization_id}).to_list()
    
    counts = {"overdue": 0, "due_soon": 0, "upcoming": 0, "completed": 0, "total": 0}
    for t in tasks:
        status_name = t.status
        if status_name in counts:
            counts[status_name] += 1
            counts["total"] += 1
            
    summary = TasksSummary(**counts)
    
    response_data = CompanyDetailResponse(
        id=company.id,
        cin=company.cin,
        name=company.name,
        company_type=company.company_type,
        reg_date=company.reg_date,
        financial_year_end=company.financial_year_end,
        address=company.address,
        assigned_to=company.assigned_to,
        relationship_partner_id=company.relationship_partner_id,
        manager_id=company.manager_id,
        assigned_team_id=company.assigned_team_id,
        primary_executive_id=company.primary_executive_id,
        is_active=company.is_active,
        created_at=company.created_at,
        tasks_summary=summary
    )
    return response_data

@clients_router.put("/{company_id}/assignment", response_model=CompanyResponse)
@router.put("/{company_id}/assignment", response_model=CompanyResponse)
async def update_client_assignment(
    company_id: uuid.UUID,
    assignment: ClientAssignmentUpdate,
    current_user: User = Depends(get_current_user),
):
    company = await _company_for_user(company_id, current_user)
    assignee_id = await _resolve_team_assignee(assignment, current_user.organization_id)
    assignment_keys = ("relationship_partner_id", "manager_id", "assigned_team_id", "primary_executive_id")
    old_assignment = {key: str(getattr(company, key)) if getattr(company, key) else None for key in assignment_keys}
    _apply_assignment(company, assignment, assignee_id)
    await company.save()
    await AuditLog(user_id=current_user.id, organization_id=current_user.organization_id,
                   action="client_assignment_updated", entity_type="company", entity_id=company.id,
                   action_metadata={"old": old_assignment, "new": {
                       **assignment.model_dump(mode="json"),
                       "primary_executive_id": str(assignee_id),
                   }}).insert()
    return company

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    company_in: CompanyUpdate,
    current_user: User = Depends(get_current_user)
):
    company = await _company_for_user(company_id, current_user)
        
    update_data = company_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await company.save()

    # Log audit: company updated
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="company_updated",
        entity_type="company",
        entity_id=company.id,
        action_metadata={"fields_updated": list(update_data.keys())}
    )
    await audit.insert()

    return company

@router.delete("/{company_id}", response_model=CompanyResponse)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    company = await _company_for_user(company_id, current_user)
        
    company.is_active = False  # Soft delete
    await company.save()

    # Log audit: company soft-deleted
    audit = AuditLog(
        user_id=current_user.id, organization_id=current_user.organization_id,
        action="company_deleted",
        entity_type="company",
        entity_id=company.id,
        action_metadata={"cin": company.cin, "name": company.name}
    )
    await audit.insert()

    return company

@router.get("/{company_id}/tasks", response_model=List[TaskResponse])
async def get_company_tasks(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    company = await _company_for_user(company_id, current_user)
        
    tasks = await Task.find({"company_id": company_id, "organization_id": current_user.organization_id}).sort("due_date").to_list()
    
    # Resolve related fields manually
    response_tasks = []
    user_cache = {}
    
    for t in tasks:
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
            
        company_min = CompanyMinResponse(
            id=company.id, name=company.name, cin=company.cin, company_type=company.company_type
        )
        
        response_tasks.append(
            TaskResponse(
                id=t.id,
                company_id=t.company_id,
                rule_id=t.rule_id,
                title=t.title,
                description=t.description,
                due_date=t.due_date,
                status=t.status,
                assigned_to=t.assigned_to,
                completed_by=t.completed_by,
                completed_at=t.completed_at,
                reference_doc=t.reference_doc,
                notes=t.notes,
                created_at=t.created_at,
                updated_at=t.updated_at,
                company=company_min,
                assigned_user=assigned_user
            )
        )
    return response_tasks

@router.get("/{company_id}/audit-logs", response_model=List[AuditLogMinResponse])
async def get_company_audit_logs(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    company = await _company_for_user(company_id, current_user)
        
    tasks = await Task.find({"company_id": company_id, "organization_id": current_user.organization_id}).to_list()
    task_ids = [t.id for t in tasks]
    
    logs = await AuditLog.find({"organization_id": current_user.organization_id,
        "$or": [
            {"entity_type": "company", "entity_id": company_id},
            {"entity_type": "task", "entity_id": {"$in": task_ids}}
        ]
    }).sort("-created_at").to_list()
    
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
    return response_logs
