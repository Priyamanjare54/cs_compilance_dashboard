from types import SimpleNamespace
import uuid
import pytest
from unittest.mock import AsyncMock
from app.routers.clients import _find_default_team, _find_default_partner, _find_default_manager


class _Query:
    def __init__(self, values):
        self.values = values

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self):
        return self.values


@pytest.mark.asyncio
async def test_find_default_team_by_industry(monkeypatch):
    org_id = uuid.uuid4()
    company = SimpleNamespace(
        id=uuid.uuid4(),
        name="ABC Pvt Ltd",
        company_type="private_limited",
        reg_date="2025-01-01",
        financial_year_end="2026-03-31",
        organization_id=org_id,
        industry="ROC services",
        assigned_team_id=None,
        assigned_team=None
    )
    teams = [
        SimpleNamespace(id=uuid.uuid4(), organization_id=org_id, name="ROC Team", manager_id=None, member_ids=[]),
        SimpleNamespace(id=uuid.uuid4(), organization_id=org_id, name="Technology Team", manager_id=None, member_ids=[]),
    ]
    monkeypatch.setattr("app.models.team.Team.find", lambda *args, **kwargs: _Query(teams))
    team = await _find_default_team(company, org_id)
    assert team is not None
    assert team.name == "ROC Team"


@pytest.mark.asyncio
async def test_find_default_manager_uses_designation(monkeypatch):
    org_id = uuid.uuid4()
    active_manager = SimpleNamespace(id=uuid.uuid4(), organization_id=org_id, is_active=True, full_name="Priya Patel")
    team = SimpleNamespace(id=uuid.uuid4(), organization_id=org_id, manager_id=active_manager.id, member_ids=[])
    monkeypatch.setattr("app.models.user.User.get", AsyncMock(return_value=active_manager))
    manager_id = await _find_default_manager(team, org_id)
    assert manager_id == active_manager.id


@pytest.mark.asyncio
async def test_find_default_partner_uses_role_or_designation(monkeypatch):
    org_id = uuid.uuid4()
    partner = SimpleNamespace(id=uuid.uuid4(), organization_id=org_id, is_active=True, full_name="Amit Verma")
    partner_query = [partner]
    monkeypatch.setattr("app.models.user.User.find", lambda *args, **kwargs: _Query(partner_query))
    partner_id = await _find_default_partner(org_id)
    assert partner_id == partner.id
