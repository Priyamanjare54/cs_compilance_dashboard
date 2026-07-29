from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from datetime import date, timedelta
from typing import List, Optional
from app.core.dependencies import get_current_user
from app.models.company import Company
from app.models.task import Task
from app.models.user import User
from app.models.team import Team
from app.models.audit_log import AuditLog
from app.schemas.report import SummaryReportResponse, CompanyReportResponse, UserTasksReport
from app.schemas.task import AuditLogMinResponse, UserMinResponse

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/partner-dashboard")
async def get_partner_dashboard(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Portfolio-level measures for partners; no unapproved task records leave this endpoint."""
    company_query = {"is_active": True, "organization_id": current_user.organization_id}
    if category == "cs":
        company_query["client_type"] = {"$in": ["cs", "both"]}
    elif category == "ca":
        company_query["client_type"] = {"$in": ["ca", "both"]}
    companies = await Company.find(company_query).to_list()
    company_ids = [company.id for company in companies]
    task_query = {"organization_id": current_user.organization_id, "company_id": {"$in": company_ids}}
    if category:
        task_query["category"] = category
    tasks = await Task.find(task_query).to_list()

    today = date.today()
    open_tasks = [task for task in tasks if task.status != "closed"]
    overdue = [task for task in open_tasks if task.due_date < today]
    todays_due = [task for task in open_tasks if task.due_date == today]
    upcoming_due = [task for task in open_tasks if today < task.due_date <= today + timedelta(days=7)]
    high_risk_company_ids = {task.company_id for task in overdue}
    closed_count = sum(task.status == "closed" for task in tasks)
    productivity = round((closed_count / len(tasks) * 100) if tasks else 100)

    teams = await Team.find({"organization_id": current_user.organization_id}).to_list()
    teams_by_id = {team.id: team.name for team in teams}
    delayed_by_team = {}
    for task in overdue:
        key = task.assigned_team_id or task.assigned_team
        delayed_by_team[key] = delayed_by_team.get(key, 0) + 1
    top_team_id = max(delayed_by_team, key=delayed_by_team.get, default=None)

    users = await User.find({"organization_id": current_user.organization_id, "is_active": True}).to_list()
    users_by_id = {user.id: user.full_name or user.email for user in users}
    closed_by_user = {}
    for task in tasks:
        if task.status == "closed" and task.completed_by:
            closed_by_user[task.completed_by] = closed_by_user.get(task.completed_by, 0) + 1
    top_user_id = max(closed_by_user, key=closed_by_user.get, default=None)

    company_names = {company.id: company.name for company in companies}
    delayed_by_company = {}
    overdue_tasks = []
    for task in overdue:
        delayed_by_company[task.company_id] = delayed_by_company.get(task.company_id, 0) + 1
        overdue_tasks.append(task)
    top_company_id = max(delayed_by_company, key=delayed_by_company.get, default=None)

    delayed_tasks = [
        {
            "id": str(task.id),
            "company_id": task.company_id,
            "company_name": company_names.get(task.company_id, "Unknown client"),
            "title": task.title,
            "assigned_name": users_by_id.get(task.assigned_to) or users_by_id.get(task.assigned_user) or "Unassigned",
            "assigned_user_id": str(task.assigned_to or task.assigned_user) if (task.assigned_to or task.assigned_user) else None,
            "delay_days": (today - task.due_date).days,
            "due_date": task.due_date,
            "status": task.status,
        }
        for task in sorted(overdue_tasks, key=lambda item: item.due_date)
    ]

    return {
        "clients": len(companies),
        "pending_filings": len(open_tasks),
        "completed": closed_count,
        "delayed": len(overdue),
        "todays_due": len(todays_due),
        "high_risk_clients": len(high_risk_company_ids),
        "team_productivity": productivity,
        "upcoming_due": len(upcoming_due),
        "top_delayed_team": teams_by_id.get(top_team_id, "No delayed team"),
        "top_performer": users_by_id.get(top_user_id, "No completed work yet"),
        "most_delayed_client": company_names.get(top_company_id, "No delayed client"),
        "delayed_tasks": delayed_tasks,
    }

@router.get("/summary", response_model=SummaryReportResponse)
async def get_summary_report(
    category: Optional[str] = None,  # cs, ca
    current_user: User = Depends(get_current_user)
):
    # Filter active companies by workspace category
    query_comp = {"is_active": True, "organization_id": current_user.organization_id}
    if category == "cs":
        query_comp["client_type"] = {"$in": ["cs", "both"]}
    elif category == "ca":
        query_comp["client_type"] = {"$in": ["ca", "both"]}
        
    total_companies = await Company.find(query_comp).count()
    
    # Filter tasks by workspace category
    query_task = {"organization_id": current_user.organization_id}
    if category is not None:
        query_task["category"] = category
        
    tasks = await Task.find(query_task).to_list()
    
    counts = {"overdue": 0, "due_soon": 0, "upcoming": 0, "completed": 0, "total": 0}
    for t in tasks:
        st = t.status
        if st in counts:
            counts[st] += 1
            counts["total"] += 1
            
    return {
        "total_companies": total_companies,
        "total_tasks": counts["total"],
        "overdue_count": counts["overdue"],
        "completed_count": counts["completed"],
        "due_soon_count": counts["due_soon"]
    }

@router.get("/company/{company_id}", response_model=CompanyReportResponse)
async def get_company_report(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    comp = await Company.get(company_id)
    if not comp or comp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Company not found")
        
    tasks = await Task.find({"company_id": company_id, "organization_id": current_user.organization_id}).to_list()
    
    counts = {"overdue": 0, "due_soon": 0, "upcoming": 0, "completed": 0, "total": 0}
    for t in tasks:
        st = t.status
        if st in counts:
            counts[st] += 1
            counts["total"] += 1
            
    score = (counts["completed"] / counts["total"] * 100) if counts["total"] > 0 else 100.0
    
    return {
        "company_id": company_id,
        "company_name": comp.name,
        "compliance_score": round(score, 1),
        "total_tasks": counts["total"],
        "completed_tasks": counts["completed"],
        "overdue_tasks": counts["overdue"]
    }

@router.get("/team", response_model=List[UserTasksReport])
async def get_team_report(
    current_user: User = Depends(get_current_user)
):
    users = await User.find({"is_active": True, "organization_id": current_user.organization_id}).to_list()
    
    reports = []
    for user in users:
        tot_cnt = await Task.find({"assigned_to": user.id, "organization_id": current_user.organization_id}).count()
        comp_cnt = await Task.find({"assigned_to": user.id, "status": "completed", "organization_id": current_user.organization_id}).count()
        
        rate = (comp_cnt / tot_cnt * 100) if tot_cnt > 0 else 100.0
        
        reports.append({
            "user_id": user.id,
            "user_name": user.full_name or user.email,
            "total_tasks": tot_cnt,
            "completed_tasks": comp_cnt,
            "completion_rate": round(rate, 1)
        })
        
    return reports

@router.get("/audit-logs", response_model=List[AuditLogMinResponse])
async def get_audit_logs(
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    logs = await AuditLog.find({"organization_id": current_user.organization_id}).sort("-created_at").limit(limit).to_list()
    
    response_logs = []
    user_cache = {}
    
    for log in logs:
        log_user = None
        if log.user_id:
            if log.user_id not in user_cache:
                u = await User.get(log.user_id)
                if u and u.organization_id == current_user.organization_id:
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

@router.get("/companies", response_model=List[CompanyReportResponse])
async def get_companies_reports(
    current_user: User = Depends(get_current_user)
):
    companies = await Company.find({"is_active": True, "organization_id": current_user.organization_id}).to_list()
    
    reports = []
    for comp in companies:
        tasks = await Task.find({"company_id": comp.id, "organization_id": current_user.organization_id}).to_list()
        
        counts = {"overdue": 0, "due_soon": 0, "upcoming": 0, "completed": 0, "total": 0}
        for t in tasks:
            st = t.status
            if st in counts:
                counts[st] += 1
                counts["total"] += 1
                
        score = (counts["completed"] / counts["total"] * 100) if counts["total"] > 0 else 100.0
        
        reports.append({
            "company_id": comp.id,
            "company_name": comp.name,
            "compliance_score": round(score, 1),
            "total_tasks": counts["total"],
            "completed_tasks": counts["completed"],
            "overdue_tasks": counts["overdue"]
        })
        
    return reports
