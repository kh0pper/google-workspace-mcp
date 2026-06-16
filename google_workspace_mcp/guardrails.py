"""
Google Docs API guardrails — encodes documented pitfalls as reusable functions.

Each function addresses a specific failure mode documented in auto-memory:
- fix_heading_inheritance: heading style leaks to inserted body text
- paginated_comments: comments API truncates at 20 without pagination
"""

import functools
import logging
from typing import Any, Callable

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def handle_google_errors(func: Callable) -> Callable:
    """
    Decorator for MCP tools. Catches Google API errors and returns structured dicts.

    Handles:
    - HttpError 401: attempts one token refresh, retries once
    - HttpError 429: includes Retry-After hint
    - HttpError 403/404/other: descriptive error message
    - Network errors: connection failures
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except HttpError as e:
            status = e.resp.status if hasattr(e, "resp") else 0

            if status == 401:
                # Try one token refresh
                try:
                    from .auth import refresh_services
                    refresh_services()
                    return await func(*args, **kwargs)
                except Exception as retry_err:
                    return {
                        "success": False,
                        "error": f"Authentication failed after refresh: {retry_err}",
                    }

            if status == 429:
                retry_after = ""
                if hasattr(e, "resp") and "retry-after" in (e.resp.headers or {}):
                    retry_after = f" Retry after {e.resp.headers['retry-after']}s."
                return {
                    "success": False,
                    "error": f"Rate limited by Google API.{retry_after}",
                }

            return {
                "success": False,
                "error": f"Google API error ({status}): {e._get_reason() if hasattr(e, '_get_reason') else str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {type(e).__name__}: {e}",
            }

    return wrapper


def build_heading_inheritance_fix(
    start_index: int, end_index: int
) -> dict:
    """
    Build a NORMAL_TEXT reset request for content inserted after a heading.

    Addresses: reference_gdocs_api_quirks.md — insertText after a heading
    causes all inserted paragraphs to inherit the heading's namedStyleType.

    Args:
        start_index: Start of the inserted content range
        end_index: End of the inserted content range

    Returns:
        An updateParagraphStyle request dict
    """
    return {
        "updateParagraphStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index,
            },
            "paragraphStyle": {
                "namedStyleType": "NORMAL_TEXT",
            },
            "fields": "namedStyleType",
        }
    }
