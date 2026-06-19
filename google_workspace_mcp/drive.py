"""
Google Drive API tools — folder listing, search, metadata.
"""

import asyncio
import base64
import logging
from typing import Optional

from .auth import get_drive_service
from .guardrails import handle_google_errors

logger = logging.getLogger(__name__)

MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_GDOC = "application/vnd.google-apps.document"


@handle_google_errors
async def gdrive_list_folder(folder_id: str) -> dict:
    """List ALL files in a Google Drive folder by ID. Paginates through every
    page (pageSize 1000 + pageToken loop), so the result is NOT capped at 100 —
    use for a complete folder inventory."""
    drive = get_drive_service()

    files = []
    page_token = None
    while True:
        result = await asyncio.to_thread(
            lambda token=page_token: drive.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                orderBy="name",
                pageSize=1000,
                pageToken=token,
            ).execute()
        )
        files.extend(result.get("files", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return {
        "success": True,
        "data": {
            "folder_id": folder_id,
            "count": len(files),
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "mime_type": f.get("mimeType", ""),
                    "modified_time": f.get("modifiedTime", ""),
                    "size": f.get("size"),
                }
                for f in files
            ],
        },
    }


@handle_google_errors
async def gdrive_find_folder(
    folder_name: str, parent_id: Optional[str] = None
) -> dict:
    """Find a folder by name, optionally within a parent folder."""
    drive = get_drive_service()

    query = f"name = '{folder_name}' and mimeType = '{MIME_FOLDER}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    result = await asyncio.to_thread(
        lambda: drive.files().list(
            q=query, spaces="drive",
            fields="files(id, name, parents)",
        ).execute()
    )

    files = result.get("files", [])
    if not files:
        return {
            "success": True,
            "data": {"found": False, "folder_name": folder_name},
        }

    return {
        "success": True,
        "data": {
            "found": True,
            "folder_id": files[0]["id"],
            "folder_name": files[0]["name"],
            "parents": files[0].get("parents", []),
        },
    }


@handle_google_errors
async def gdrive_get_metadata(file_id: str) -> dict:
    """Get file/document metadata (modified time, parents, etc.)."""
    drive = get_drive_service()

    result = await asyncio.to_thread(
        lambda: drive.files().get(
            fileId=file_id,
            fields="id, name, mimeType, modifiedTime, createdTime, parents, webViewLink, size, shortcutDetails",
        ).execute()
    )

    return {
        "success": True,
        "data": {
            "id": result["id"],
            "name": result["name"],
            "mime_type": result.get("mimeType", ""),
            "modified_time": result.get("modifiedTime", ""),
            "created_time": result.get("createdTime", ""),
            "parents": result.get("parents", []),
            "web_view_link": result.get("webViewLink"),
            "size": result.get("size"),
            # For shortcuts: {"targetId": ..., "targetMimeType": ...} so the
            # real target can be resolved/moved; absent for non-shortcut files.
            "shortcut_details": result.get("shortcutDetails"),
        },
    }


@handle_google_errors
async def gdrive_get_permissions(file_id: str) -> dict:
    """List every sharing permission on a Drive file/folder (who can see it). READ-ONLY —
    does not change sharing. Returns each permission's type/role/email/domain plus a
    convenience `anyone_with_link` flag (True if a type='anyone' permission exists) for
    sharing audits. Paginates fully (no cap)."""
    drive = get_drive_service()

    permissions = []
    page_token = None
    while True:
        result = await asyncio.to_thread(
            lambda token=page_token: drive.permissions().list(
                fileId=file_id,
                fields="nextPageToken, permissions(id, type, role, emailAddress, domain, displayName, allowFileDiscovery, deleted)",
                pageSize=100,
                supportsAllDrives=True,
                pageToken=token,
            ).execute()
        )
        permissions.extend(result.get("permissions", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    cleaned = [
        {
            "id": p.get("id"),
            "type": p.get("type"),
            "role": p.get("role"),
            "email": p.get("emailAddress"),
            "domain": p.get("domain"),
            "display_name": p.get("displayName"),
            # For type='anyone'/'domain': False = link-only, True = discoverable/searchable.
            "allow_file_discovery": p.get("allowFileDiscovery"),
            "deleted": p.get("deleted", False),
        }
        for p in permissions
    ]
    anyone = [p for p in cleaned if p["type"] == "anyone"]

    return {
        "success": True,
        "data": {
            "file_id": file_id,
            "count": len(cleaned),
            # True means anyone-with-the-link can open it.
            "anyone_with_link": bool(anyone),
            "permissions": cleaned,
        },
    }


@handle_google_errors
async def gdrive_read_file(
    file_id: str, export_mime_type: Optional[str] = None, max_chars: int = 200000
) -> dict:
    """Read a Drive file's raw content as text (READ-ONLY). For UPLOADED files (CSV/TSV/TXT/JSON
    and similar) it downloads the bytes (files.get_media) and returns UTF-8 text. For binary files
    it returns base64 (encoding='base64'). For Google-native files (Docs/Sheets/Slides) you must
    pass export_mime_type (e.g. 'text/csv', 'text/plain') — but prefer the dedicated gdocs_/sheets_
    tools for those. Content is capped at max_chars (truncated=True if cut)."""
    drive = get_drive_service()
    meta = await asyncio.to_thread(
        lambda: drive.files().get(
            fileId=file_id, fields="id, name, mimeType, size", supportsAllDrives=True
        ).execute()
    )
    mime = meta.get("mimeType", "")
    name = meta.get("name")

    if mime.startswith("application/vnd.google-apps"):
        export_mt = export_mime_type or "text/plain"
        raw = await asyncio.to_thread(
            lambda: drive.files().export(fileId=file_id, mimeType=export_mt).execute()
        )
    else:
        raw = await asyncio.to_thread(
            lambda: drive.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
        )

    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    try:
        text = raw.decode("utf-8")
        return {
            "success": True,
            "data": {
                "file_id": file_id,
                "name": name,
                "mime_type": mime,
                "encoding": "text",
                "truncated": len(text) > max_chars,
                "content": text[:max_chars],
            },
        }
    except UnicodeDecodeError:
        b64 = base64.b64encode(raw).decode("ascii")
        return {
            "success": True,
            "data": {
                "file_id": file_id,
                "name": name,
                "mime_type": mime,
                "encoding": "base64",
                "truncated": len(b64) > max_chars,
                "content": b64[:max_chars],
            },
        }


@handle_google_errors
async def gdrive_search(query: str, max_results: int = 20) -> dict:
    """Search Drive by name pattern. Searches non-trashed files."""
    drive = get_drive_service()

    search_query = f"name contains '{query}' and trashed = false"

    result = await asyncio.to_thread(
        lambda: drive.files().list(
            q=search_query,
            spaces="drive",
            fields="files(id, name, mimeType, modifiedTime, parents)",
            orderBy="modifiedTime desc",
            pageSize=max_results,
        ).execute()
    )

    files = result.get("files", [])
    return {
        "success": True,
        "data": {
            "query": query,
            "count": len(files),
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "mime_type": f.get("mimeType", ""),
                    "modified_time": f.get("modifiedTime", ""),
                    "parents": f.get("parents", []),
                }
                for f in files
            ],
        },
    }


@handle_google_errors
async def gdrive_create_folder(
    name: str, parent_id: Optional[str] = None
) -> dict:
    """Create a Drive folder. Idempotent: if a folder with the same name already
    exists in the same parent, returns that folder instead of creating a duplicate.
    Returns data.folder_id, data.created (True if newly created, False if reused)."""
    drive = get_drive_service()

    safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"name = '{safe_name}' and mimeType = '{MIME_FOLDER}' and trashed = false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    result = await asyncio.to_thread(
        lambda: drive.files().list(
            q=query, spaces="drive",
            fields="files(id, name, parents, webViewLink)",
        ).execute()
    )
    files = result.get("files", [])
    if files:
        return {
            "success": True,
            "data": {
                "folder_id": files[0]["id"],
                "name": files[0]["name"],
                "parents": files[0].get("parents", []),
                "web_view_link": files[0].get("webViewLink"),
                "created": False,
            },
        }

    metadata = {"name": name, "mimeType": MIME_FOLDER}
    if parent_id:
        metadata["parents"] = [parent_id]

    created = await asyncio.to_thread(
        lambda: drive.files().create(
            body=metadata,
            fields="id, name, parents, webViewLink",
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "folder_id": created["id"],
            "name": created["name"],
            "parents": created.get("parents", []),
            "web_view_link": created.get("webViewLink"),
            "created": True,
        },
    }


@handle_google_errors
async def gdrive_move_file(file_id: str, new_parent_id: str) -> dict:
    """Move a file into a new parent folder. Removes all OTHER parents so the
    file ends up only under new_parent_id. No-op (moved=False) if the file is
    already only in new_parent_id."""
    drive = get_drive_service()

    current = await asyncio.to_thread(
        lambda: drive.files().get(
            fileId=file_id, fields="id, name, parents"
        ).execute()
    )
    cur_parents = current.get("parents", []) or []

    if cur_parents == [new_parent_id]:
        return {
            "success": True,
            "data": {
                "id": current["id"],
                "name": current.get("name"),
                "parents": cur_parents,
                "moved": False,
            },
        }

    remove = ",".join(p for p in cur_parents if p != new_parent_id)

    update_kwargs = {
        "fileId": file_id,
        "addParents": new_parent_id,
        "fields": "id, name, parents",
    }
    if remove:
        update_kwargs["removeParents"] = remove

    result = await asyncio.to_thread(
        lambda: drive.files().update(**update_kwargs).execute()
    )
    return {
        "success": True,
        "data": {
            "id": result["id"],
            "name": result.get("name"),
            "parents": result.get("parents", []),
            "moved": True,
        },
    }


@handle_google_errors
async def gdrive_copy_file(
    file_id: str, new_title: Optional[str] = None, parent_id: Optional[str] = None
) -> dict:
    """Copy a Drive file (incl. Google Sheets/Docs and their bound Apps Script)
    and return the new file's id. `new_title` (optional) names the copy;
    `parent_id` (optional) places it in a folder, else it lands in My Drive root.

    Use this to make a safe sandbox/test copy before mutating a production file.
    Caveat: a copied Sheet keeps its IMPORTRANGE formulas but they need
    re-authorization in the copy, and any add-on configs still point at the
    originals until repointed — fine for a read/logic test copy.
    """
    drive = get_drive_service()
    body: dict = {}
    if new_title:
        body["name"] = new_title
    if parent_id:
        body["parents"] = [parent_id]
    result = await asyncio.to_thread(
        lambda: drive.files().copy(
            fileId=file_id, body=body, fields="id, name, parents, mimeType"
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "id": result["id"],
            "name": result.get("name"),
            "parents": result.get("parents", []),
            "mime_type": result.get("mimeType"),
            "source_file_id": file_id,
        },
    }


@handle_google_errors
async def gdrive_trash_file(file_id: str) -> dict:
    """Move a file to the Trash (recoverable for ~30 days; NOT a permanent
    delete). Use to clean up sandbox/test copies you created. Confirm intent
    before calling — this hides the file from normal views."""
    drive = get_drive_service()
    result = await asyncio.to_thread(
        lambda: drive.files().update(
            fileId=file_id, body={"trashed": True}, fields="id, name, trashed"
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "id": result["id"],
            "name": result.get("name"),
            "trashed": result.get("trashed", True),
        },
    }


@handle_google_errors
async def gdrive_rename(file_id: str, new_name: str) -> dict:
    """Rename a Drive file or folder. Changes the display name ONLY — the file ID
    is unchanged, so links, add-on configs, IMPORTRANGE, and anything that
    references the item by ID keep working. Returns old_name + name
    (renamed=False if the name was already new_name)."""
    drive = get_drive_service()
    current = await asyncio.to_thread(
        lambda: drive.files().get(fileId=file_id, fields="id, name").execute()
    )
    old_name = current.get("name")
    if old_name == new_name:
        return {
            "success": True,
            "data": {
                "id": current["id"],
                "old_name": old_name,
                "name": old_name,
                "renamed": False,
            },
        }
    result = await asyncio.to_thread(
        lambda: drive.files().update(
            fileId=file_id, body={"name": new_name}, fields="id, name"
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "id": result["id"],
            "old_name": old_name,
            "name": result.get("name"),
            "renamed": True,
        },
    }


@handle_google_errors
async def gdrive_transfer_ownership(file_id: str, new_owner_email: str) -> dict:
    """Transfer ownership of a Drive file/folder to another user (by email). Within the
    SAME Google Workspace domain the transfer is immediate; for consumer/cross-domain the
    recipient must accept first (returns pending_owner=True). IMPORTANT: transferring a
    FOLDER does NOT re-own the files inside it — every item keeps its own owner, so to
    re-home a whole tree you must transfer each contained file too (walk the tree)."""
    drive = get_drive_service()
    result = await asyncio.to_thread(
        lambda: drive.permissions().create(
            fileId=file_id,
            body={"type": "user", "role": "owner", "emailAddress": new_owner_email},
            transferOwnership=True,
            sendNotificationEmail=True,
            fields="id, role, emailAddress, pendingOwner",
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "file_id": file_id,
            "new_owner": new_owner_email,
            "permission_id": result.get("id"),
            "role": result.get("role"),
            "pending_owner": result.get("pendingOwner", False),
        },
    }


@handle_google_errors
async def gdrive_create_shortcut(
    target_id: str, parent_id: str, name: Optional[str] = None
) -> dict:
    """Create a Drive shortcut (a pointer) to target_id, placed inside parent_id. If
    name is omitted, the shortcut takes the target's name. Works across drives — e.g. a
    shortcut in a Shared Drive that points at a My Drive folder (supportsAllDrives)."""
    drive = get_drive_service()
    shortcut_name = name
    if not shortcut_name:
        target = await asyncio.to_thread(
            lambda: drive.files().get(
                fileId=target_id, fields="name", supportsAllDrives=True
            ).execute()
        )
        shortcut_name = target.get("name")
    body = {
        "name": shortcut_name,
        "mimeType": "application/vnd.google-apps.shortcut",
        "parents": [parent_id],
        "shortcutDetails": {"targetId": target_id},
    }
    result = await asyncio.to_thread(
        lambda: drive.files().create(
            body=body,
            fields="id, name, parents, shortcutDetails",
            supportsAllDrives=True,
        ).execute()
    )
    return {
        "success": True,
        "data": {
            "id": result["id"],
            "name": result.get("name"),
            "parents": result.get("parents", []),
            "target_id": target_id,
        },
    }
