from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.routers.reports import get_partner_dashboard


class _Query:
    def __init__(self, values):
        self.values = values

    async def to_list(self):
        return self.values


@pytest.mark.asyncio
async def test_partner_dashboard_returns_expected_metrics(monkeypatch):
    org_id = uuid.uuid4()
    company_id = uuid.uuid4()
    team_id = uuid.uuid4()
    assignee_id = uuid.uuid4()
    closed_by_id = uuid.uuid4()

    current_user = SimpleNamespace(organization_id=org_id)

    companies = [
        SimpleNamespace(id=company_id, name="ABC Pvt Ltd", is_active=True, organization_id=org_id),
    ]

    users = [
        SimpleNamespace(id=assignee_id, full_name="Rahul", email="rahul@example.com", role="executive", organization_id=org_id, is_active=True),
        SimpleNamespace(id=closed_by_id, full_name="Priya", email="priya@example.com", role="executive", organization_id=org_id, is_active=True),
    ]

    tasks = [
        SimpleNamespace(
            id=uuid.uuid4(),
            company_id=company_id,
            title="Annual Return Filing",
            assigned_to=assignee_id,
            assigned_user=None,
            due_date=date.today() - timedelta(days=5),
            status="pending",
            assigned_team_id=team_id,
            assigned_team=None,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            company_id=company_id,
            title="Board Meeting Minutes",
            assigned_to=assignee_id,
            assigned_user=None,
            due_date=date.today(),
            status="in_progress",
            assigned_team_id=team_id,
            assigned_team=None,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            company_id=company_id,
            title="Director KYC",
            assigned_to=closed_by_id,
            assigned_user=None,
            due_date=date.today() - timedelta(days=2),
            status="closed",
            completed_by=closed_by_id,
            assigned_team_id=team_id,
            assigned_team=None,
        ),
    ]

    teams = [
        SimpleNamespace(id=team_id, name="ROC Team", organization_id=org_id),
    ]

    monkeypatch.setattr("app.routers.reports.Company.find", lambda *args, **kwargs: _Query(companies))
    monkeypatch.setattr("app.routers.reports.Task.find", lambda *args, **kwargs: _Query(tasks))
    monkeypatch.setattr("app.routers.reports.Team.find", lambda *args, **kwargs: _Query(teams))
    monkeypatch.setattr("app.routers.reports.User.find", lambda *args, **kwargs: _Query(users))

    response = await get_partner_dashboard(category=None, current_user=current_user)

    assert response["clients"] == 1
    assert response["pending_filings"] == 2
    assert response["completed"] == 1
    assert response["delayed"] == 1
    assert response["todays_due"] == 1
    assert response["top_delayed_team"] == "ROC Team"
    assert response["top_performer"] == "Priya"
    assert response["delayed_tasks"]
    overdue_task = response["delayed_tasks"][0]
    assert overdue_task["company_name"] == "ABC Pvt Ltd"
    assert overdue_task["assigned_name"] == "Rahul"
    assert overdue_task["delay_days"] == 5
