import asyncio
from app.core.db import init_db
from app.models.company import Company
from app.models.task import Task
from app.models.compliance_calendar import ComplianceCalendar

async def main():
    print("Initializing database connection...")
    await init_db()

    company_res = await Company.get_pymongo_collection().delete_many({})
    task_res = await Task.get_pymongo_collection().delete_many({})
    cal_res = await ComplianceCalendar.get_pymongo_collection().delete_many({})

    print(f"Deleted {company_res.deleted_count} documents from companies collection")
    print(f"Deleted {task_res.deleted_count} documents from tasks collection")
    print(f"Deleted {cal_res.deleted_count} documents from compliance_calendar collection")

if __name__ == "__main__":
    asyncio.run(main())
