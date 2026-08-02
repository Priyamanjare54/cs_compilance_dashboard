from datetime import timedelta, date
from typing import Optional
import uuid
import logging
from app.models.company import Company
from app.models.compliance_rule import ComplianceRule
from app.models.task import Task
from app.models.audit_log import AuditLog
from app.models.compliance_calendar import ComplianceCalendar

logger = logging.getLogger(__name__)

async def run_rule_engine_for_company(db, company: Company, user_id: Optional[uuid.UUID] = None) -> int:
    """
    Given a company, find matching active rules, compute due dates,
    bulk create tasks, and write an audit log.
    Returns the count of tasks generated.
    """
    # Query active rules matching the company client type and rule category
    category_filter = []
    client_type = getattr(company, "client_type", "cs") or "cs"
    if client_type == "cs":
        category_filter = ["cs"]
    elif client_type == "ca":
        category_filter = ["ca"]
    else:
        category_filter = ["cs", "ca"]

    rules = await ComplianceRule.find({
        "is_active": True,
        "category": {"$in": category_filter},
        "$or": [{"organization_id": company.organization_id}, {"organization_id": None}],
    }).to_list()
    
    tasks_to_create = []
    calendar_items = []
    generated_count = 0
    
    for rule in rules:
        if company.company_type in rule.company_types:
            # Check financial thresholds (null threshold = no restriction; rule applies regardless)
            if rule.min_paid_up_capital is not None and (company.paid_up_capital is None or company.paid_up_capital < rule.min_paid_up_capital):
                continue
            if rule.min_annual_turnover is not None and (company.annual_turnover is None or company.annual_turnover < rule.min_annual_turnover):
                continue
            if rule.min_bank_loan_amount is not None and (company.bank_loan_amount is None or company.bank_loan_amount < rule.min_bank_loan_amount):
                continue

            due_date = company.financial_year_end + timedelta(days=rule.due_days_from_trigger)
            
            title = f"{rule.name} ({rule.form_number})" if rule.form_number else rule.name
            description = rule.description or f"Compliance requirement: {title}"
            
            task = Task(
                company_id=company.id,
                organization_id=company.organization_id,
                rule_id=rule.id,
                title=title,
                description=description,
                due_date=due_date,
                status="pending",
                assigned_to=company.assigned_to,
                assigned_user=company.assigned_to,
                assigned_user_id=company.assigned_to,
                assigned_team_id=company.assigned_team_id,
                created_by=user_id,
                category=rule.category
            )
            tasks_to_create.append(task)
            calendar_items.append(ComplianceCalendar(
                organization_id=company.organization_id,
                client_id=company.id,
                compliance_rule_id=rule.id,
                due_date=due_date,
                status="overdue" if due_date < date.today() else "scheduled",
                frequency=rule.frequency,
            ))
            generated_count += 1
            
    if tasks_to_create:
        # Bulk insert
        await Task.insert_many(tasks_to_create)
        await ComplianceCalendar.insert_many(calendar_items)
        
        # Log to audit logs
        audit_log = AuditLog(
            user_id=user_id,
            organization_id=company.organization_id,
            action="tasks_generated",
            entity_type="company",
            entity_id=company.id,
            action_metadata={
                "company_name": company.name,
                "tasks_count": generated_count, "calendar_items_count": len(calendar_items),
                "task_titles": [t.title for t in tasks_to_create]
            }
        )
        await audit_log.insert()
        
    return generated_count
