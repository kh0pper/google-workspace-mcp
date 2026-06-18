"""
Google Drive API tools — folder listing, search, metadata.
"""

import asyncio
import logging
from typing import Optional

from .auth import get_drive_service
from .guardrails import handle_google_errors

logger = logging.getLogger(__name__)

MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_GDOC = "application/vnd.google-apps.document"


@handle_google_errors
async def gdrive_list_folder(folder_id: str) -> dict:
    """List files in a Google Drive folder by ID."""
    drive = get_drive_service()

    result = await asyncio.to_thread(
        lambda: drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            spaces="drive",
            fields="files(id, name, mimeType, modifiedTime, size)",
            orderBy="name",
        ).execute()
    )

    files = result.get("files", [])
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
