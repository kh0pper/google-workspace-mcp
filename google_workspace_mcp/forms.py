"""
Google Forms API v1 tools — read a form's structure and EDIT it in place
(add / update / delete questions) without recreating it, so the published
responder URL (QR codes, flyers, prior emails) is preserved.

Requirements:
  - the `forms.body` scope granted (see auth.SCOPES) — needs a re-auth after the
    scope is added;
  - the Google Forms API enabled in the OAuth client's GCP project
    (console.cloud.google.com -> APIs & Services -> enable "Google Forms API").

Forms model: a form has `info` (title/description) and an ordered list of `items`,
each with an `itemId`. A question item carries a `question` with a `questionId`,
`required`, and one of choiceQuestion / textQuestion / scaleQuestion / etc.
Editing is via forms.batchUpdate with createItem / updateItem / deleteItem requests;
createItem needs a `location.index` (append = current item count).

NOTE: this module deliberately does NOT read form responses. Add a separate,
clearly-scoped tool with forms.responses.readonly if that is ever needed.
"""

import asyncio
import logging

from .auth import get_forms_service
from .guardrails import handle_google_errors

logger = logging.getLogger(__name__)

# Map a friendly question type -> how to build its question body.
_CHOICE_TYPES = {"CHECKBOX", "RADIO", "DROP_DOWN"}


def _summarize_item(item: dict) -> dict:
    """Reduce a raw Forms item to a compact digest for forms_get_structure."""
    out = {"item_id": item.get("itemId"), "title": item.get("title", "")}
    if "pageBreakItem" in item:
        out["kind"] = "page_break (section)"
        return out
    if "textItem" in item:
        out["kind"] = "text (descriptive)"
        return out
    if "imageItem" in item:
        out["kind"] = "image"
        return out
    if "videoItem" in item:
        out["kind"] = "video"
        return out
    qi = item.get("questionItem")
    if qi:
        q = qi.get("question", {})
        out["question_id"] = q.get("questionId")
        out["required"] = bool(q.get("required", False))
        if "choiceQuestion" in q:
            cq = q["choiceQuestion"]
            out["kind"] = "choice"
            out["choice_type"] = cq.get("type")  # RADIO | CHECKBOX | DROP_DOWN
            out["options"] = [o.get("value") for o in cq.get("options", [])]
        elif "textQuestion" in q:
            out["kind"] = "paragraph_text" if q["textQuestion"].get("paragraph") else "short_text"
        elif "scaleQuestion" in q:
            out["kind"] = "scale"
        elif "dateQuestion" in q:
            out["kind"] = "date"
        elif "timeQuestion" in q:
            out["kind"] = "time"
        elif "fileUploadQuestion" in q:
            out["kind"] = "file_upload"
        else:
            out["kind"] = "question (other)"
        return out
    if "questionGroupItem" in item:
        out["kind"] = "question_group (grid)"
        return out
    out["kind"] = "other"
    return out


@handle_google_errors
async def forms_get_structure(form_id: str) -> dict:
    """Read a form's structure: title, the responder (public) URL, the linked
    response sheet if any, and every item as a compact digest (item_id, title,
    kind, and for choice questions: choice_type + options + required)."""
    svc = get_forms_service()
    res = await asyncio.to_thread(lambda: svc.forms().get(formId=form_id).execute())
    items = res.get("items", [])
    info = res.get("info", {})
    return {
        "success": True,
        "data": {
            "form_id": res.get("formId", form_id),
            "title": info.get("title", ""),
            "document_title": info.get("documentTitle", ""),
            "description": info.get("description", ""),
            "responder_uri": res.get("responderUri", ""),
            "revision_id": res.get("revisionId", ""),
            "linked_sheet_id": res.get("linkedSheetId"),
            "item_count": len(items),
            "items": [_summarize_item(it) for it in items],
        },
    }


@handle_google_errors
async def forms_batch_update(form_id: str, requests: list) -> dict:
    """Advanced: raw forms.batchUpdate passthrough. `requests` is a list of
    Forms API request objects (createItem / updateItem / deleteItem / moveItem /
    updateFormInfo / updateSettings). Returns the new revisionId + replies.
    Editing an existing form by id PRESERVES its published URL."""
    svc = get_forms_service()
    body = {"requests": requests, "includeFormInResponse": False}
    res = await asyncio.to_thread(
        lambda: svc.forms().batchUpdate(formId=form_id, body=body).execute()
    )
    return {
        "success": True,
        "data": {
            "form_id": form_id,
            "revision_id": res.get("form", {}).get("revisionId")
            or res.get("writeControl", {}).get("requiredRevisionId"),
            "replies": res.get("replies", []),
        },
    }


@handle_google_errors
async def forms_add_question(
    form_id: str,
    title: str,
    type: str = "CHECKBOX",
    options: list | None = None,
    required: bool = False,
    index: int | None = None,
) -> dict:
    """Add ONE question to an existing form in place (URL preserved).

    `type`: CHECKBOX | RADIO | DROP_DOWN (need `options`), or SHORT_TEXT | PARAGRAPH.
    `options`: list of choice strings (choice types only).
    `required`: default False.
    `index`: 0-based position among items; None appends at the end.

    For choice types each option string becomes a {"value": ...}. Returns the new
    item's id (from the createItem reply)."""
    svc = get_forms_service()
    t = (type or "").upper()

    if index is None:
        cur = await asyncio.to_thread(lambda: svc.forms().get(formId=form_id).execute())
        index = len(cur.get("items", []))

    question: dict = {"required": bool(required)}
    if t in _CHOICE_TYPES:
        if not options:
            return {
                "success": False,
                "error": f"type {t} requires a non-empty `options` list.",
                "data": {"form_id": form_id},
            }
        question["choiceQuestion"] = {
            "type": t,
            "options": [{"value": str(o)} for o in options],
        }
    elif t in ("SHORT_TEXT", "TEXT"):
        question["textQuestion"] = {"paragraph": False}
    elif t in ("PARAGRAPH", "PARAGRAPH_TEXT"):
        question["textQuestion"] = {"paragraph": True}
    else:
        return {
            "success": False,
            "error": f"unsupported type {t!r}; use CHECKBOX|RADIO|DROP_DOWN|SHORT_TEXT|PARAGRAPH.",
            "data": {"form_id": form_id},
        }

    request = {
        "createItem": {
            "item": {"title": title, "questionItem": {"question": question}},
            "location": {"index": int(index)},
        }
    }
    body = {"requests": [request], "includeFormInResponse": False}
    res = await asyncio.to_thread(
        lambda: svc.forms().batchUpdate(formId=form_id, body=body).execute()
    )
    replies = res.get("replies", [])
    new_id = None
    if replies and "createItem" in replies[0]:
        new_id = replies[0]["createItem"].get("itemId")
    return {
        "success": True,
        "data": {
            "form_id": form_id,
            "created_item_id": new_id,
            "index": index,
            "title": title,
            "type": t,
        },
    }
