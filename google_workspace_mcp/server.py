"""
Google Workspace MCP Server.

Unified Drive, Docs, Sheets, Slides, Gmail, and Calendar tools with built-in
guardrails. No full-document replace tool exists (deliberate — prevents
formatting destruction).
"""

import logging
from typing import Optional

from fastmcp import FastMCP

from . import docs, drive, comments, gmail, sheets, slides, apps_script
from . import calendar as gcal_mod

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "google-workspace",
    instructions="""
Google Workspace MCP server — unified access to Google Drive, Docs, Sheets,
Slides, Gmail, and Calendar, using the user's own OAuth credentials.

Key guardrails built into this server:
- No full-document replace tool (prevents formatting/chart destruction)
- gdocs_insert_at_heading auto-resets NORMAL_TEXT (prevents heading style inheritance)
- gdocs_list_comments uses full pagination (no truncation at 20)
- gdocs_replace_section uses heading-to-heading delete+reinsert (safe for reference lists)
- gdocs_find_replace batch mode is atomic (single batchUpdate, prevents edit duplication)
- No raw email send except gmail_send_to_self, which is restricted to an opt-in allowlist
""",
)


# --- Docs Tools ---

@mcp.tool()
async def gdocs_read(doc_id: str) -> dict:
    """Read a Google Doc as markdown via rich structure reading. Always hits live API (no caching)."""
    return await docs.gdocs_read(doc_id)


@mcp.tool()
async def gdocs_get_structure(doc_id: str) -> dict:
    """Return the heading outline with index positions for a Google Doc."""
    return await docs.gdocs_get_structure(doc_id)


@mcp.tool()
async def gdocs_read_section(doc_id: str, heading: str) -> dict:
    """Read a single section by heading name. Reduces token usage vs reading the full doc."""
    return await docs.gdocs_read_section(doc_id, heading)


@mcp.tool()
async def gdocs_find_replace(
    doc_id: str,
    find: Optional[str] = None,
    replace: Optional[str] = None,
    match_case: bool = True,
    pairs: Optional[list[dict]] = None,
) -> dict:
    """
    Find-replace in a Google Doc, preserving formatting.

    Single mode: provide find + replace strings.
    Batch mode: provide pairs=[{"find": "old", "replace": "new"}, ...].
    Batch executes as a single atomic batchUpdate call.
    """
    return await docs.gdocs_find_replace(
        doc_id, find=find, replace=replace, match_case=match_case, pairs=pairs
    )


@mcp.tool()
async def gdocs_append(doc_id: str, markdown: str) -> dict:
    """Append formatted markdown content to the end of a Google Doc."""
    return await docs.gdocs_append(doc_id, markdown)


@mcp.tool()
async def gdocs_insert_at_heading(doc_id: str, heading: str, markdown: str) -> dict:
    """
    Insert formatted markdown content after a specific heading.
    Auto-applies NORMAL_TEXT reset to prevent heading style inheritance.
    """
    return await docs.gdocs_insert_at_heading(doc_id, heading, markdown)


@mcp.tool()
async def gdocs_replace_section(doc_id: str, heading: str, markdown: str) -> dict:
    """
    Replace content between two headings using safe delete+reinsert.
    Preserves the heading itself; replaces everything until the next same-or-higher-level heading.
    """
    return await docs.gdocs_replace_section(doc_id, heading, markdown)


@mcp.tool()
async def gdocs_create(
    folder_id: str,
    title: str,
    content: str = "",
    find_existing: bool = True,
) -> dict:
    """
    Create a new Google Doc in a folder. With find_existing=True (default),
    returns existing doc with same title instead of creating a duplicate.
    """
    return await docs.gdocs_create(
        folder_id, title, content=content, find_existing=find_existing
    )


@mcp.tool()
async def gdocs_rewrite_passages(
    doc_id: str,
    passages: list[dict],
) -> dict:
    """
    Rewrite specific paragraphs in a doc by anchored start-text match.

    Each item in passages must have:
      - match_prefix (str): the first 30-100 characters of the paragraph to
        rewrite. The tool strips leading whitespace from each paragraph and
        checks if it startswith this prefix. Case-sensitive.
      - new_text (str): the rewritten paragraph text. May contain '\\n' to
        produce multiple paragraphs in place of the original single one.

    Reliable for prose-scale rule application (e.g. removing em-dashes by
    REWRITING sentences, not substituting punctuation). Each paragraph is
    replaced as a unit via deleteContentRange + insertText, batched in reverse
    document order so index shifts don't break later operations.

    Returns per-passage match status and lengths. Pairs whose prefix didn't
    match any paragraph are reported in results and leave the doc unchanged.

    Trade-off: replacement is plain text — bold/italic/link formatting inside
    the replaced paragraph is lost. Use when content correctness matters more
    than preserving inline formatting.
    """
    return await docs.gdocs_rewrite_passages(doc_id, passages)


# --- Drive Tools ---

@mcp.tool()
async def gdrive_list_folder(folder_id: str) -> dict:
    """List all files in a Google Drive folder."""
    return await drive.gdrive_list_folder(folder_id)


@mcp.tool()
async def gdrive_find_folder(
    folder_name: str, parent_id: Optional[str] = None
) -> dict:
    """Find a folder by name, optionally within a parent folder."""
    return await drive.gdrive_find_folder(folder_name, parent_id)


@mcp.tool()
async def gdrive_get_metadata(file_id: str) -> dict:
    """Get metadata for a file or document (modified time, parents, web link)."""
    return await drive.gdrive_get_metadata(file_id)


@mcp.tool()
async def gdrive_search(query: str, max_results: int = 20) -> dict:
    """Search Google Drive by name pattern."""
    return await drive.gdrive_search(query, max_results)


@mcp.tool()
async def gdrive_create_folder(
    name: str, parent_id: Optional[str] = None
) -> dict:
    """Create a Drive folder. Idempotent: if a folder with the same name already exists in the same parent, returns that folder's id instead of creating a duplicate. Returns data.folder_id and data.created (True if newly created, False if reused)."""
    return await drive.gdrive_create_folder(name, parent_id)


@mcp.tool()
async def gdrive_move_file(file_id: str, new_parent_id: str) -> dict:
    """Move a file into a new parent folder. Removes all OTHER parents so the file ends up only under new_parent_id. No-op (data.moved=False) if the file is already only in new_parent_id."""
    return await drive.gdrive_move_file(file_id, new_parent_id)


@mcp.tool()
async def gdrive_copy_file(
    file_id: str, new_title: Optional[str] = None, parent_id: Optional[str] = None
) -> dict:
    """Copy a Drive file (incl. Sheets/Docs + their bound Apps Script); returns the new file id. `new_title` names
    the copy; `parent_id` places it in a folder. Use to make a safe sandbox/test copy before mutating production.
    Caveat: a copied Sheet's IMPORTRANGE needs re-auth in the copy, and add-on configs still point at the originals."""
    return await drive.gdrive_copy_file(file_id, new_title=new_title, parent_id=parent_id)


@mcp.tool()
async def gdrive_trash_file(file_id: str) -> dict:
    """Move a file to Trash (recoverable ~30 days; NOT a permanent delete). Use to clean up sandbox/test copies you made. Confirm intent first."""
    return await drive.gdrive_trash_file(file_id)


@mcp.tool()
async def gdrive_rename(file_id: str, new_name: str) -> dict:
    """Rename a Drive file or folder. Changes the display name ONLY — the file ID is unchanged, so links, add-on configs, IMPORTRANGE, and anything that references it by ID keep working. Returns old_name + name."""
    return await drive.gdrive_rename(file_id, new_name)


# --- Comments Tools ---

@mcp.tool()
async def gdocs_list_comments(
    doc_id: str, include_resolved: bool = False
) -> dict:
    """
    List ALL comments on a Google Doc with full pagination.
    Uses pageSize=100 + nextPageToken loop (no truncation at 20).
    """
    return await comments.gdocs_list_comments(doc_id, include_resolved)


@mcp.tool()
async def gdocs_add_comment(
    doc_id: str, content: str, quoted_text: Optional[str] = None
) -> dict:
    """Add a comment to a Google Doc, optionally anchored to specific text."""
    return await comments.gdocs_add_comment(doc_id, content, quoted_text)


@mcp.tool()
async def gdocs_reply_comment(
    doc_id: str, comment_id: str, content: str
) -> dict:
    """Reply to a comment on a Google Doc."""
    return await comments.gdocs_reply_comment(doc_id, comment_id, content)


@mcp.tool()
async def gdocs_resolve_comment(doc_id: str, comment_id: str) -> dict:
    """Resolve a comment on a Google Doc."""
    return await comments.gdocs_resolve_comment(doc_id, comment_id)


@mcp.tool()
async def gdocs_apply_comment_edit(
    doc_id: str, comment_id: str, replace_text: str, summary: str
) -> dict:
    """Atomic: apply edit from comment + reply with summary + resolve.

    The tool fetches the comment's authoritative quotedFileContent.value from
    Drive and uses THAT as the find target — the agent never has to preserve
    long verbatim strings through reasoning. Agent supplies only:
      - replace_text: the new text to substitute for the highlighted region.
      - summary: a one-sentence description of the change for the comment reply.

    Returns success even when the highlighted text can't be located (e.g. doc
    edited since the comment); in that case it leaves a 'could not locate'
    reply, resolves the comment, and sets data.applied = false.
    """
    return await comments.gdocs_apply_comment_edit(
        doc_id, comment_id, replace_text, summary
    )


# --- Gmail Tools ---

@mcp.tool()
async def gmail_search_threads(query: str, max_results: int = 20) -> dict:
    """
    Search Gmail threads using Gmail's query syntax.
    Examples: 'from:alice@example.com', 'newer_than:7d label:inbox',
    '-label:newsletter subject:meeting'. Returns light hydration
    (subject/from/snippet); use gmail_get_thread for full bodies.
    """
    return await gmail.gmail_search_threads(query, max_results)


@mcp.tool()
async def gmail_get_thread(thread_id: str) -> dict:
    """Get the full content of a Gmail thread (all messages with headers and plain-text bodies)."""
    return await gmail.gmail_get_thread(thread_id)


@mcp.tool()
async def gmail_create_draft(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict:
    """
    Create a Gmail draft (NOT sent — lands in Drafts). If `thread_id` is
    provided, the draft is attached to that thread with proper threading
    headers so external clients also see it as a reply.
    """
    return await gmail.gmail_create_draft(to, subject, body, thread_id=thread_id, cc=cc, bcc=bcc)


@mcp.tool()
async def gmail_create_threaded_reply(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
) -> dict:
    """
    Create a Gmail draft as a REPLY on an existing thread. Identical to
    gmail_create_draft except thread_id is REQUIRED — this variant exists for
    pipelines that must thread, so the schema forces the caller to supply
    thread_id instead of relying on prompt discipline. The draft lands in
    Drafts (NOT sent) and carries the correct In-Reply-To / References headers
    so external clients see it as a reply.
    """
    return await gmail.gmail_create_draft(to, subject, body, thread_id=thread_id)


@mcp.tool()
async def gmail_send_to_self(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """
    SEND (not draft) an email to an allowlisted self address. Use this for
    digest-STARTING messages that intentionally open a new Gmail thread. For
    REPLIES that must stay on an existing thread, use
    gmail_send_threaded_to_self instead — that variant requires thread_id at
    the schema level so the threading bug (LLM omitting thread_id) is
    impossible.

    Body is rendered as both plain text and markdown-converted HTML in a
    multipart/alternative message so Gmail renders the formatting (headings,
    lists, tables, links) properly instead of leaving raw markdown visible.

    DO NOT use for external recipients — the recipient must be in the self-send
    allowlist, which is EMPTY by default (set GMAIL_SEND_TO_SELF_ALLOWLIST=
    your@address to enable). For drafts to external recipients, use
    gmail_create_draft.
    """
    return await gmail.gmail_send_to_self(to, subject, body, thread_id=thread_id, reply_to=reply_to)


@mcp.tool()
async def gmail_send_threaded_to_self(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
) -> dict:
    """
    SEND (not draft) an email to an allowlisted self address, THREADED on
    an existing Gmail thread. thread_id is REQUIRED — this tool errors at
    the schema level if it's omitted. Use this for replies that must stay on
    an existing conversation.

    Requiring thread_id at the schema level means the agent can't accidentally
    open a new Gmail thread by forgetting the parameter. For digest-STARTING
    messages where a fresh thread is the intent, use gmail_send_to_self.

    Body is rendered as both plain text and markdown-converted HTML so Gmail
    formats it properly. Recipient must be in the self-send allowlist (EMPTY by
    default; set GMAIL_SEND_TO_SELF_ALLOWLIST=your@address to enable).
    """
    if not thread_id or not thread_id.strip():
        return {
            "success": False,
            "error": (
                "gmail_send_threaded_to_self requires a non-empty thread_id. "
                "For digest-STARTING messages, use gmail_send_to_self instead."
            ),
        }
    return await gmail.gmail_send_to_self(to, subject, body, thread_id=thread_id)


@mcp.tool()
async def gmail_label_thread(
    thread_id: str,
    add_labels: Optional[list[str]] = None,
    remove_labels: Optional[list[str]] = None,
) -> dict:
    """
    Add or remove labels on a Gmail thread. Accepts label names OR IDs;
    system labels (INBOX, UNREAD, STARRED, IMPORTANT, SPAM, TRASH, SENT, DRAFT)
    always work by name.
    """
    return await gmail.gmail_label_thread(thread_id, add_labels=add_labels, remove_labels=remove_labels)


@mcp.tool()
async def gmail_archive(thread_id: str) -> dict:
    """Archive a Gmail thread (removes INBOX label)."""
    return await gmail.gmail_archive(thread_id)


@mcp.tool()
async def gmail_list_labels() -> dict:
    """List all Gmail labels (system + user) with counts."""
    return await gmail.gmail_list_labels()


@mcp.tool()
async def gmail_create_label(
    name: str,
    label_list_visibility: str = "labelShow",
    message_list_visibility: str = "show",
) -> dict:
    """
    Create a new Gmail user label. Use "/" to nest (e.g. "projects/alpha"
    creates a label nested under "projects"). Idempotent: returns the existing
    id with already_existed=true if the name is already taken.
    """
    return await gmail.gmail_create_label(name, label_list_visibility, message_list_visibility)


@mcp.tool()
async def gmail_create_filter(
    add_labels: Optional[list[str]] = None,
    remove_labels: Optional[list[str]] = None,
    from_address: Optional[str] = None,
    to_address: Optional[str] = None,
    subject: Optional[str] = None,
    query: Optional[str] = None,
    negated_query: Optional[str] = None,
    has_attachment: Optional[bool] = None,
    exclude_chats: Optional[bool] = None,
    mark_as_read: bool = False,
    archive: bool = False,
    forward: Optional[str] = None,
) -> dict:
    """
    Create a Gmail filter rule. At least one criterion (from_address,
    to_address, subject, query, etc.) and one action (add_labels,
    remove_labels, mark_as_read, archive, forward) are required. Filters
    are immutable in Gmail — to edit one, delete via UI and recreate.
    """
    return await gmail.gmail_create_filter(
        add_labels=add_labels, remove_labels=remove_labels,
        from_address=from_address, to_address=to_address, subject=subject,
        query=query, negated_query=negated_query, has_attachment=has_attachment,
        exclude_chats=exclude_chats, mark_as_read=mark_as_read, archive=archive,
        forward=forward,
    )


# --- Calendar Tools ---

@mcp.tool()
async def gcal_list_calendars() -> dict:
    """List all Google calendars the user has access to."""
    return await gcal_mod.gcal_list_calendars()


@mcp.tool()
async def gcal_list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 20,
    query: Optional[str] = None,
    single_events: bool = True,
) -> dict:
    """
    List events in a Google calendar. time_min/time_max are RFC3339
    (e.g. '2026-04-22T00:00:00Z'); omit both to get events starting from
    now. `calendar_id` defaults to 'primary'.
    """
    return await gcal_mod.gcal_list_events(
        calendar_id=calendar_id, time_min=time_min, time_max=time_max,
        max_results=max_results, query=query, single_events=single_events,
    )


@mcp.tool()
async def gcal_get_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Fetch full details for a specific event."""
    return await gcal_mod.gcal_get_event(event_id, calendar_id)


@mcp.tool()
async def gcal_create_event(
    summary: str,
    start: str,
    end: str,
    calendar_id: str = "primary",
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    send_updates: str = "none",
) -> dict:
    """
    Create a Google Calendar event. start/end are RFC3339 timestamps or
    date strings ('2026-04-23' → all-day). send_updates defaults to
    'none' for draft-like behavior; pass 'all' to actually send invites.
    """
    return await gcal_mod.gcal_create_event(
        summary=summary, start=start, end=end, calendar_id=calendar_id,
        description=description, location=location, attendees=attendees,
        send_updates=send_updates,
    )


@mcp.tool()
async def gcal_respond_to_event(
    event_id: str,
    response: str,
    calendar_id: str = "primary",
    comment: Optional[str] = None,
) -> dict:
    """Respond to a calendar invitation. `response` must be accepted/declined/tentative."""
    return await gcal_mod.gcal_respond_to_event(
        event_id, response, calendar_id=calendar_id, comment=comment,
    )


# --- Sheets Tools ---

@mcp.tool()
async def sheets_list(spreadsheet_id: str) -> dict:
    """List the sheet/tab names in a Google Spreadsheet."""
    return await sheets.sheets_list(spreadsheet_id)


@mcp.tool()
async def sheets_read(
    spreadsheet_id: str, range: str, value_render_option: str = "FORMATTED_VALUE"
) -> dict:
    """Read cell values from an A1 range. `range` is a tab name ('Sheet1') or A1 range ('Sheet1!A1:E50').
    `value_render_option`: FORMATTED_VALUE (default), UNFORMATTED_VALUE, or FORMULA (returns the cell's formula
    like '=IF(K2<>"",K2,J2)' instead of its result — use to inspect/trace formulas)."""
    return await sheets.sheets_read(spreadsheet_id, range, value_render_option=value_render_option)


@mcp.tool()
async def sheets_write(
    spreadsheet_id: str, range: str, values: list, value_input_option: str = "USER_ENTERED"
) -> dict:
    """Write a 2D array of values into an A1 range (overwrites). `values` is a list of rows: [["a","b"],["c","d"]]."""
    return await sheets.sheets_write(spreadsheet_id, range, values, value_input_option=value_input_option)


@mcp.tool()
async def sheets_append(
    spreadsheet_id: str, sheet_name: str, values: list, value_input_option: str = "USER_ENTERED"
) -> dict:
    """Append a row to the end of a tab. `values` is one row (["Item A","2","ea"]) or a list of rows."""
    return await sheets.sheets_append(spreadsheet_id, sheet_name, values, value_input_option=value_input_option)


@mcp.tool()
async def sheets_add_tab(
    spreadsheet_id: str, title: str, rows: int = 1000, columns: int = 26, index: int | None = None
) -> dict:
    """Create a new tab/sheet in a spreadsheet. `index` (optional) sets its 0-based position. Returns the new sheet_id."""
    return await sheets.sheets_add_tab(spreadsheet_id, title, rows=rows, columns=columns, index=index)


@mcp.tool()
async def sheets_rename_tab(spreadsheet_id: str, title: str, new_title: str) -> dict:
    """Rename a tab from `title` to `new_title`."""
    return await sheets.sheets_rename_tab(spreadsheet_id, title, new_title)


@mcp.tool()
async def sheets_delete_tab(spreadsheet_id: str, title: str) -> dict:
    """Delete a tab by name. DESTRUCTIVE — confirm intent before calling."""
    return await sheets.sheets_delete_tab(spreadsheet_id, title)


@mcp.tool()
async def sheets_set_number_format(
    spreadsheet_id: str, range: str, pattern: str = "@", format_type: str = "TEXT"
) -> dict:
    """Set a range's number format (range must name a tab, e.g. 'Sheet1!A2:A200'). Defaults force plain TEXT ('@')
    so IDs / leading-zero codes / dates are stored verbatim. format_type: TEXT|NUMBER|PERCENT|CURRENCY|DATE|TIME|DATE_TIME|SCIENTIFIC."""
    return await sheets.sheets_set_number_format(spreadsheet_id, range, pattern=pattern, format_type=format_type)


# --- Apps Script Tools (read/edit/push .gs project source; run functions) ---

@mcp.tool()
async def apps_script_get_content(script_id: str) -> dict:
    """Read every file in an Apps Script project (the .gs source + appsscript.json manifest + any HTML). `script_id`
    is the project's Script ID (Apps Script editor -> Project Settings -> IDs; for a bound script, open it via the
    container's Extensions -> Apps Script)."""
    return await apps_script.apps_script_get_content(script_id)


@mcp.tool()
async def apps_script_update_file(
    script_id: str, file_name: str, source: str, file_type: str = "SERVER_JS"
) -> dict:
    """Replace the source of ONE file in an Apps Script project, leaving the manifest and other files untouched
    (fetches current content, swaps the named file, pushes the full set back). `file_name` has NO extension
    ('Code', not 'Code.gs') — use the name from apps_script_get_content. `file_type` (new files only): SERVER_JS|HTML|JSON."""
    return await apps_script.apps_script_update_file(script_id, file_name, source, file_type=file_type)


@mcp.tool()
async def apps_script_update_content(script_id: str, files: list) -> dict:
    """Advanced: replace the ENTIRE project file set. `files` = list of {name, type, source}; MUST include the
    manifest ({"name":"appsscript","type":"JSON","source":"{...}"}). Prefer apps_script_update_file for single edits."""
    return await apps_script.apps_script_update_content(script_id, files)


@mcp.tool()
async def apps_script_run(
    script_id: str, function_name: str, parameters: list | None = None, dev_mode: bool = True
) -> dict:
    """Run a function via scripts.run and return its result. REQUIRES the script deployed as an API Executable and
    its GCP project == this OAuth client's project (often not possible for container-bound scripts without moving
    them to a standard GCP project). Returns success=False with the structured error on a script-side failure."""
    return await apps_script.apps_script_run(script_id, function_name, parameters=parameters, dev_mode=dev_mode)


# --- Slides Tools (Phase 1: read + notes-safe find/replace) ---

@mcp.tool()
async def gslides_read(presentation_id: str, include_notes: bool = True) -> dict:
    """Read a Google Slides deck into a per-slide digest (shapes, object ids, and speaker notes)."""
    return await slides.gslides_read(presentation_id, include_notes=include_notes)


@mcp.tool()
async def gslides_get_structure(presentation_id: str) -> dict:
    """Light outline of a deck: slide ids, titles, and element ids for navigation."""
    return await slides.gslides_get_structure(presentation_id)


@mcp.tool()
async def gslides_read_notes(presentation_id: str, slide_id: Optional[str] = None) -> dict:
    """Read speaker-notes text per slide (read-only); optionally a single slide."""
    return await slides.gslides_read_notes(presentation_id, slide_id=slide_id)


@mcp.tool()
async def gslides_find_replace(
    presentation_id: str,
    find: Optional[str] = None,
    replace: Optional[str] = None,
    match_case: bool = True,
    scope: str = "slides",
    slide_ids: Optional[list[str]] = None,
    pairs: Optional[list[dict]] = None,
) -> dict:
    """
    Find-replace deck text, preserving formatting. scope is the speaker-notes safety gate:
    "slides" (default, notes-safe), "notes", or "all". Single (find+replace) or batch (pairs).
    A 0 occurrence count means the literal find string did not match, not a no-op success.
    """
    return await slides.gslides_find_replace(
        presentation_id,
        find=find,
        replace=replace,
        match_case=match_case,
        scope=scope,
        slide_ids=slide_ids,
        pairs=pairs,
    )


# --- Slides Tools (Phase 2: authoring) ---

@mcp.tool()
async def gslides_create(title: str, folder_id: Optional[str] = None) -> dict:
    """Create a new Google Slides presentation; optionally move it into a Drive folder."""
    return await slides.gslides_create(title, folder_id=folder_id)


@mcp.tool()
async def gslides_add_slide(presentation_id: str, layout: str = "BLANK", index: Optional[int] = None) -> dict:
    """Add a slide by predefined layout (BLANK, TITLE, TITLE_AND_BODY, SECTION_HEADER, ...)."""
    return await slides.gslides_add_slide(presentation_id, layout=layout, index=index)


@mcp.tool()
async def gslides_duplicate_slide(presentation_id: str, slide_id: str) -> dict:
    """Duplicate a slide and its contents; returns the new slide id."""
    return await slides.gslides_duplicate_slide(presentation_id, slide_id)


@mcp.tool()
async def gslides_delete_slide(presentation_id: str, slide_id: str) -> dict:
    """Delete a slide (or any object) by id."""
    return await slides.gslides_delete_slide(presentation_id, slide_id)


@mcp.tool()
async def gslides_reorder_slides(presentation_id: str, slide_ids: list, insertion_index: int) -> dict:
    """Move the given slide ids to a new position."""
    return await slides.gslides_reorder_slides(presentation_id, slide_ids, insertion_index)


@mcp.tool()
async def gslides_add_text_box(
    presentation_id: str,
    slide_id: str,
    text: str,
    x: float = 1.0,
    y: float = 1.0,
    width: float = 8.0,
    height: float = 1.0,
    font_size: Optional[float] = None,
) -> dict:
    """Add a text box (geometry in inches) to a slide and fill it with text."""
    return await slides.gslides_add_text_box(
        presentation_id, slide_id, text, x=x, y=y, width=width, height=height, font_size=font_size
    )


@mcp.tool()
async def gslides_add_image(
    presentation_id: str,
    slide_id: str,
    image_url: str,
    x: float = 1.0,
    y: float = 1.0,
    width: float = 4.0,
    height: float = 3.0,
) -> dict:
    """Add an image by public URL to a slide (geometry in inches)."""
    return await slides.gslides_add_image(
        presentation_id, slide_id, image_url, x=x, y=y, width=width, height=height
    )


@mcp.tool()
async def gslides_format_text(
    presentation_id: str,
    object_id: str,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    underline: Optional[bool] = None,
    font_size: Optional[float] = None,
    color_hex: Optional[str] = None,
    font_family: Optional[str] = None,
) -> dict:
    """Style all text in a shape (bold/italic/underline/font_size/color_hex/font_family)."""
    return await slides.gslides_format_text(
        presentation_id, object_id, bold=bold, italic=italic, underline=underline,
        font_size=font_size, color_hex=color_hex, font_family=font_family,
    )


@mcp.tool()
async def gslides_format_paragraph(
    presentation_id: str, object_id: str, alignment: Optional[str] = None
) -> dict:
    """Set paragraph alignment for all text in a shape (START, CENTER, END, JUSTIFIED)."""
    return await slides.gslides_format_paragraph(presentation_id, object_id, alignment=alignment)


@mcp.tool()
async def gslides_edit_text(presentation_id: str, object_id: str, new_text: str) -> dict:
    """Replace all text in one shape, re-applying the first run's style (bold/size/color survive)."""
    return await slides.gslides_edit_text(presentation_id, object_id, new_text)


@mcp.tool()
async def gslides_edit_notes(
    presentation_id: str, slide_id: str, text: str, mode: str = "replace"
) -> dict:
    """Replace or append a slide's speaker notes (deliberate notes edit). mode: 'replace' | 'append'."""
    return await slides.gslides_edit_notes(presentation_id, slide_id, text, mode=mode)


@mcp.tool()
async def gslides_batch_update(presentation_id: str, requests: list) -> dict:
    """Raw Slides API batchUpdate passthrough (power tool). `requests` is a list of request dicts."""
    return await slides.gslides_batch_update(presentation_id, requests)


@mcp.tool()
async def gslides_export(presentation_id: str, fmt: str = "pdf", out_path: Optional[str] = None) -> dict:
    """Export the deck to a local file via Drive. fmt: 'pdf' or 'pptx'. Returns the path."""
    return await slides.gslides_export(presentation_id, fmt=fmt, out_path=out_path)


def main():
    """Entry point for google-workspace-mcp."""
    mcp.run()


if __name__ == "__main__":
    main()
