from datetime import date, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.models.task import Task
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.services.notifications import create_notification
import logging
import uuid

logger = logging.getLogger(__name__)

async def _get_task_manager_id(task: Task) -> uuid.UUID | None:
    team_id = task.assigned_team_id or task.assigned_team
    if team_id:
        team = await Team.get(team_id)
        if team and team.organization_id == task.organization_id:
            return team.manager_id

    company = await Company.get(task.company_id)
    if company and company.organization_id == task.organization_id:
        return company.manager_id

    return None

async def _get_task_partner_id(task: Task) -> uuid.UUID | None:
    company = await Company.get(task.company_id)
    if company and company.organization_id == task.organization_id:
        return company.relationship_partner_id or task.approver_id or task.approver
    return task.approver_id or task.approver

async def run_daily_compliance_check():
    """
    Evaluate deadline notifications for active tasks.
    If a task changes to 'overdue', trigger notifier.py
    """
    logger.info("Starting daily compliance check job...")
    
    # Workflow status is never changed by reminders or escalations.
    tasks = await Task.find({"status": {"$ne": "closed"}}).to_list()
    
    today = date.today()
    reminder_count = 0
    
    for task in tasks:
        if not task.organization_id:
            continue

        days_to_due = (task.due_date - today).days
        if days_to_due in {7, 3, 1, 0}:
            await create_notification(
                organization_id=task.organization_id, user_id=task.assigned_to, task_id=task.id,
                type="reminders", title="Task due reminder",
                message=f"{task.title} is due {'today' if days_to_due == 0 else f'in {days_to_due} day(s)' }.",
                dedupe_key=f"task:{task.id}:reminder:{task.due_date.isoformat()}:{days_to_due}",
            )
            reminder_count += 1

            manager_id = await _get_task_manager_id(task)
            if manager_id:
                await create_notification(
                    organization_id=task.organization_id, user_id=manager_id, task_id=task.id,
                    type="reminders", title="Manager reminder: task due soon",
                    message=f"{task.title} assigned to your team is due {'today' if days_to_due == 0 else f'in {days_to_due} day(s)' }.",
                    dedupe_key=f"task:{task.id}:reminder:manager:{task.due_date.isoformat()}:{days_to_due}",
                )
                reminder_count += 1

        overdue_days = (today - task.due_date).days
        if overdue_days >= 1:
            await create_notification(
                organization_id=task.organization_id, user_id=task.assigned_to, task_id=task.id,
                type="escalations", title="Task overdue",
                message=f"{task.title} is overdue. Please resolve it immediately.",
                dedupe_key=f"task:{task.id}:overdue:executive",
            )
        if overdue_days >= 3:
            manager_id = await _get_task_manager_id(task)
            await create_notification(
                organization_id=task.organization_id, user_id=manager_id, task_id=task.id,
                type="escalations", title="Manager escalation: overdue task",
                message=f"{task.title} has been overdue for 3 days.",
                dedupe_key=f"task:{task.id}:overdue:manager",
            )
        if overdue_days >= 7:
            partner_id = await _get_task_partner_id(task)
            await create_notification(
                organization_id=task.organization_id, user_id=partner_id, task_id=task.id,
                type="escalations", title="Partner escalation: overdue task",
                message=f"{task.title} has been overdue for 7 days.",
                dedupe_key=f"task:{task.id}:overdue:partner",
            )
                        
    logger.info(f"Daily notification check completed. Processed {reminder_count} reminder events.")
scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        run_daily_compliance_check,
        trigger='cron',
        hour=8,
        minute=0,
        timezone=pytz.timezone('Asia/Kolkata'),
        id='daily_compliance_check',
        replace_existing=True
    )
    scheduler.start()
    logger.info("APScheduler started successfully for daily compliance check at 08:00 IST.")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("APScheduler shut down successfully.")
