from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from fastapi import HTTPException

from app.core.dependencies import get_current_user, require_same_organization
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.task import Task
from app.models.user import User
from app.services import scheduler
from app.routers.admin import create_user
from app.routers.clients import _resolve_team_assignee
from app.routers.organizations import TeamInput, update_team
from app.schemas.company import ClientAssignmentUpdate
from app.schemas.user import UserCreate
from app.models.team import Team


@pytest.mark.asyncio
async def test_token_cannot_be_reused_after_user_moves_workspace(monkeypatch):
    original_org = uuid.uuid4()
    current_org = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), role="admin", is_active=True, organization_id=current_org)
    monkeypatch.setattr(User, "get", AsyncMock(return_value=user))

    token = create_access_token(user.id, user.role, original_org)
    with pytest.raises(HTTPException) as error:
        await get_current_user(token)
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_suspended_workspace_is_rejected(monkeypatch):
    org_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), role="admin", is_active=True, organization_id=org_id)
    monkeypatch.setattr(User, "get", AsyncMock(return_value=user))
    monkeypatch.setattr(Organization, "get", AsyncMock(return_value=SimpleNamespace(status="suspended")))

    token = create_access_token(user.id, user.role, org_id)
    with pytest.raises(HTTPException) as error:
        await get_current_user(token)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_resource_from_another_workspace_is_hidden():
    user = SimpleNamespace(organization_id=uuid.uuid4())
    resource = SimpleNamespace(organization_id=uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        await require_same_organization(resource, user)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_platform_admin():
    request = UserCreate(email="owner@example.com", password="Secret123", role="platform_admin")
    current_user = SimpleNamespace(organization_id=uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        await create_user(request, current_user)
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_team_from_another_workspace_cannot_be_edited(monkeypatch):
    current_org = uuid.uuid4()
    foreign_team = SimpleNamespace(organization_id=uuid.uuid4())
    current_user = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=current_org,
        permissions=["can_manage_settings"],
        role_id=None,
        role="admin",
    )
    monkeypatch.setattr(Team, "get", AsyncMock(return_value=foreign_team))

    with pytest.raises(HTTPException) as error:
        await update_team(uuid.uuid4(), TeamInput(name="ROC Team"), current_user)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_client_allocation_routes_to_team_manager(monkeypatch):
    organization_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    team_manager_id = uuid.uuid4()
    member_id = uuid.uuid4()
    team = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=organization_id,
        manager_id=team_manager_id,
        member_ids=[member_id],
    )
    users = {
        user_id: SimpleNamespace(id=user_id)
        for user_id in (partner_id, manager_id, team_manager_id, member_id)
    }

    def find_users(query):
        requested_ids = query["_id"]["$in"]
        return _Query([users[user_id] for user_id in requested_ids if user_id in users])

    monkeypatch.setattr(User, "find", find_users)
    monkeypatch.setattr(Team, "get", AsyncMock(return_value=team))
    assignment = ClientAssignmentUpdate(
        relationship_partner_id=partner_id,
        manager_id=manager_id,
        assigned_team_id=team.id,
    )

    assert await _resolve_team_assignee(assignment, organization_id) == team_manager_id


@pytest.mark.asyncio
async def test_client_allocation_falls_back_to_first_active_team_member(monkeypatch):
    organization_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    inactive_member_id = uuid.uuid4()
    active_member_id = uuid.uuid4()
    team = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=organization_id,
        manager_id=None,
        member_ids=[inactive_member_id, active_member_id],
    )
    active_users = {
        user_id: SimpleNamespace(id=user_id)
        for user_id in (partner_id, manager_id, active_member_id)
    }

    def find_users(query):
        requested_ids = query["_id"]["$in"]
        return _Query([active_users[user_id] for user_id in requested_ids if user_id in active_users])

    monkeypatch.setattr(User, "find", find_users)
    monkeypatch.setattr(Team, "get", AsyncMock(return_value=team))
    assignment = ClientAssignmentUpdate(
        relationship_partner_id=partner_id,
        manager_id=manager_id,
        assigned_team_id=team.id,
    )

    assert await _resolve_team_assignee(assignment, organization_id) == active_member_id


class _Query:
    def __init__(self, values):
        self.values = values

    async def to_list(self):
        return self.values


@pytest.mark.asyncio
async def test_overdue_notifications_stay_inside_task_workspace(monkeypatch):
    first_org = uuid.uuid4()
    assignee_id = uuid.uuid4()
    task = SimpleNamespace(
        id=uuid.uuid4(),
        title="Annual filing",
        organization_id=first_org,
        assigned_to=assignee_id,
        due_date=date.today() - timedelta(days=1),
        status="assigned",
    )
    monkeypatch.setattr(Task, "find", lambda *args, **kwargs: _Query([task]))
    create_notification = AsyncMock(return_value=True)
    monkeypatch.setattr(scheduler, "create_notification", create_notification)

    await scheduler.run_daily_compliance_check()

    assert create_notification.await_count == 1
    call = create_notification.await_args
    assert call.kwargs["organization_id"] == first_org
    assert call.kwargs["user_id"] == assignee_id
