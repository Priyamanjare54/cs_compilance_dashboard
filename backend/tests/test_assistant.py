from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from fastapi import HTTPException

from app.services.assistant_search import find_relevant_records
from app.services.assistant_generation import _build_email_prompt, _parse_email_draft
from app.routers.assistant import EmailDraftRequest, _source_title, assistant_email_draft
from app.models.company import Company


def test_assistant_finds_form_related_publications():
    matches = find_relevant_records("MCA annual filing form compliance")
    assert matches
    assert all(item["url"] for item in matches)


def test_assistant_handles_unsearchable_question():
    assert find_relevant_records("the and what") == []


def test_assistant_rejects_irrelevant_question():
    assert find_relevant_records("what is the capital of France?") == []


def test_assistant_formats_scraped_source_title():
    record = find_relevant_records(
        "What is the procedure for transfer of interest of a member in a company not having share capital?"
    )[0]

    assert "Section 56" in record["title"]
    assert "form SH-4" in record["title"]
    source_title = _source_title(record["title"])
    assert len(source_title) <= 90
    assert source_title.endswith("...")


def test_email_prompt_uses_client_context_and_safety_rules():
    prompt = _build_email_prompt(
        instruction="Request the signed financial statements by Friday.",
        client_name="ABC Pvt Ltd",
        sender_name="Priya Shah",
        tone="professional",
        recipient_name="Mr. Mehta",
    )

    assert "CLIENT: ABC Pvt Ltd" in prompt
    assert "Address the recipient as Mr. Mehta" in prompt
    assert "Never invent dates, fees" in prompt
    assert "SUBJECT:" in prompt and "BODY:" in prompt


def test_email_draft_parser_returns_subject_and_body():
    draft = _parse_email_draft(
        "SUBJECT: Documents required for annual filing\nBODY:\nDear Mr. Mehta,\n\nPlease share the signed statements.\n\nRegards,\nPriya"
    )

    assert draft["subject"] == "Documents required for annual filing"
    assert draft["body"].startswith("Dear Mr. Mehta")


@pytest.mark.asyncio
async def test_executive_cannot_generate_client_email():
    user = SimpleNamespace(
        id=uuid.uuid4(), organization_id=uuid.uuid4(), designation="executive", role="executive"
    )
    request = EmailDraftRequest(
        client_id=uuid.uuid4(), prompt="Request the signed statements by Friday."
    )

    with pytest.raises(HTTPException) as error:
        await assistant_email_draft(request, user)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_partner_can_generate_email_for_tenant_client(monkeypatch):
    organization_id = uuid.uuid4()
    company = SimpleNamespace(id=uuid.uuid4(), name="ABC Pvt Ltd", organization_id=organization_id)
    user = SimpleNamespace(
        id=uuid.uuid4(), organization_id=organization_id, designation="partner",
        role="partner", full_name="Priya Shah", email="priya@example.com",
    )
    monkeypatch.setattr(Company, "get", AsyncMock(return_value=company))
    generate = AsyncMock(return_value={"subject": "Document request", "body": "Dear Client,\nPlease share the documents."})
    monkeypatch.setattr("app.routers.assistant.generate_email_draft", generate)
    request = EmailDraftRequest(
        client_id=company.id, prompt="Request the signed statements by Friday."
    )

    response = await assistant_email_draft(request, user)

    assert response["client_name"] == "ABC Pvt Ltd"
    assert response["subject"] == "Document request"
    assert generate.await_args.kwargs["sender_name"] == "Priya Shah"
