"""
Google Sheets API v4 tools — read/write/append/list cell values in a spreadsheet.
"""

import asyncio
import logging
from typing import Optional

from .auth import get_sheets_service
from .guardrails import handle_google_errors

logger = logging.getLogger(__name__)


def _scalarize(v):
    """Coerce a cell to a Sheets-API-safe scalar. The API rejects struct/array
    cells with a 400 (`Invalid values[..]: struct_value`); a stray dict/list is
    JSON-stringified rather than sent raw, so a malformed cell never hard-fails
    (and never triggers a model retry loop). None -> "".
    """
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    import json as _json
    return _json.dumps(v, ensure_ascii=False)


async def _read_header(svc, spreadsheet_id: str, sheet_name: str) -> list:
    res = await asyncio.to_thread(
        lambda: svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!1:1"
        ).execute()
    )
    vals = res.get("values", [])
    return vals[0] if vals else []


async def _coerce_rows(svc, spreadsheet_id: str, sheet_name: str, values) -> list:
    """Normalize append `values` into a 2D array of scalars.

    Accepts what an LLM naturally produces: a single dict keyed by column name,
    a list of such dicts, a single flat row (list of scalars), or a list of
    rows. Dict rows are mapped onto the sheet's header order (missing columns
    -> ""), so the caller can pass {"item": "...", "quantity": 2, ...} directly.
    """
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list) or not values:
        return []
    if any(isinstance(r, dict) for r in values):
        header = await _read_header(svc, spreadsheet_id, sheet_name)
        rows = []
        for r in values:
            if isinstance(r, dict):
                rows.append([_scalarize(r.get(col, "")) for col in header])
            elif isinstance(r, list):
                rows.append([_scalarize(c) for c in r])
            else:
                rows.append([_scalarize(r)])
        return rows
    if isinstance(values[0], list):
        return [[_scalarize(c) for c in r] for r in values]
    return [[_scalarize(c) for c in values]]


@handle_google_errors
async def sheets_list(spreadsheet_id: str) -> dict:
    """List the sheet/tab names in a spreadsheet."""
    svc = get_sheets_service()
    result = await asyncio.to_thread(
        lambda: svc.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="properties.title,sheets.properties(title,sheetId,index,gridProperties)",
        ).execute()
    )
    sheets = result.get("sheets", [])
    return {
        "success": True,
        "data": {
            "spreadsheet_id": spreadsheet_id,
            "title": result.get("properties", {}).get("title", ""),
            "count": len(sheets),
            "sheets": [
                {
                    "title": s["properties"].get("title", ""),
                    "sheet_id": s["properties"].get("sheetId"),
                    "index": s["properties"].get("index"),
                    "rows": s["properties"].get("gridProperties", {}).get("rowCount"),
                    "columns": s["properties"].get("gridProperties", {}).get("columnCount"),
                }
                for s in sheets
            ],
        },
    }


@handle_google_errors
async def sheets_read(spreadsheet_id: str, range: str) -> dict:
    """Read cell values from an A1 range (e.g. 'Sheet1' or 'Sheet1!A1:E50').

    Returns rows as a list of lists; trailing empty cells/rows are omitted by
    the API, so rows may be ragged.
    """
    svc = get_sheets_service()
    result = await asyncio.to_thread(
        lambda: svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range,
        ).execute()
    )
    values = result.get("values", [])
    return {
        "success": True,
        "data": {
            "spreadsheet_id": spreadsheet_id,
            "range": result.get("range", range),
            "row_count": len(values),
            "values": values,
        },
    }


@handle_google_errors
async def sheets_write(
    spreadsheet_id: str, range: str, values: list, value_input_option: str = "USER_ENTERED"
) -> dict:
    """Write a 2D array of values into an A1 range (overwrites existing cells).

    `values` is a list of rows, each row a list of cell values, e.g.
    [["Item A", "2", "ea", "note"]]. `value_input_option` is
    USER_ENTERED (default; parses numbers/dates like the UI) or RAW.
    """
    svc = get_sheets_service()
    # Accept a single flat row and wrap it; scalarize every cell so a stray
    # dict/array never hits the API as a struct (400).
    if isinstance(values, list) and values and not isinstance(values[0], list):
        values = [values]
    safe = [[_scalarize(c) for c in r] for r in values] if isinstance(values, list) else values
    result = await asyncio.to_thread(
        lambda: svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption=value_input_option,
            body={"values": safe},
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "spreadsheet_id": spreadsheet_id,
            "updated_range": result.get("updatedRange", range),
            "updated_rows": result.get("updatedRows", 0),
            "updated_columns": result.get("updatedColumns", 0),
            "updated_cells": result.get("updatedCells", 0),
        },
    }


@handle_google_errors
async def sheets_append(
    spreadsheet_id: str, sheet_name: str, values: list, value_input_option: str = "USER_ENTERED"
) -> dict:
    """Append one or more rows to the end of a sheet/tab.

    `sheet_name` is the tab name (e.g. 'Sheet1'); the API finds the table and
    appends after the last row. `values` is flexible — pass whichever is easiest:
      - a dict keyed by column name: {"item": "Item A", "quantity": 2, ...}
        (mapped onto the sheet's header order; unknown keys ignored, missing -> "")
      - a list of such dicts (multiple rows)
      - a flat list of cell values in column order: ["id-1", "Item A", ...]
      - a list of rows (list of lists)
    """
    svc = get_sheets_service()
    rows = await _coerce_rows(svc, spreadsheet_id, sheet_name, values)
    if not rows:
        return {"success": False, "error": "No rows to append (values was empty)."}
    result = await asyncio.to_thread(
        lambda: svc.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption=value_input_option,
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
    )
    updates = result.get("updates", {})
    return {
        "success": True,
        "data": {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "updated_range": updates.get("updatedRange", ""),
            "updated_rows": updates.get("updatedRows", 0),
            "updated_cells": updates.get("updatedCells", 0),
        },
    }
