from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from fastapi import HTTPException

from app.models.company import Company
from app.models.task import Task
from app.routers.clients import _company_for_user, get_companies
from app.routers.tasks import _task_for_user, get_tasks


class _TaskQuery:
    def __init__(self, values=None):
        self.values = values or []

    def sort(self, *_args):
        return self

    def skip(self, *_args):
        return self

    def limit(self, *_args):
        return self

    async def to_list(self):
        return self.values


@pytest.mark.asyncio
async def test_executive_task_list_is_forced_to_current_user(monkeypatch):
    organization_id = uuid.uuid4()
    executive_id = uuid.uuid4()
    captured = {}

    def find_tasks(query):
        captured.update(query)
        return _TaskQuery()

    monkeypatch.setattr(Task, "find", find_tasks)
    user = SimpleNamespace(
        id=executive_id,
        organization_id=organization_id,
        designation="Executive",
        role="executive",
    )

    await get_tasks(assigned_to=uuid.uuid4(), current_user=user)

    assert captured == {"organization_id": organization_id, "assigned_to": executive_id}


@pytest.mark.asyncio
async def test_executive_cannot_open_another_users_task(monkeypatch):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        designation="Executive",
        role="executive",
    )
    task = SimpleNamespace(organization_id=user.organization_id, assigned_to=uuid.uuid4())
    monkeypatch.setattr(Task, "get", AsyncMock(return_value=task))

    with pytest.raises(HTTPException) as error:
        await _task_for_user(uuid.uuid4(), user)

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_executive_cannot_browse_company_portfolio(monkeypatch):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        designation="Executive",
        role="executive",
    )
    find_company = AsyncMock()
    monkeypatch.setattr(Company, "get", find_company)

    assert await get_companies(current_user=user) == []
    with pytest.raises(HTTPException) as error:
        await _company_for_user(uuid.uuid4(), user)

    assert error.value.status_code == 404
    find_company.assert_not_awaited()
