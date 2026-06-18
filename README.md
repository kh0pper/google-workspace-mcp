# Google Workspace MCP Server

**English** · [Español](./README.es.md)

Give a **local‑first AI assistant** safe, structured access to **your own** Google
Workspace — Drive, Docs, Sheets, Slides, Gmail, Calendar, and Apps Script — using
your own Google account, running entirely on your computer or server. Your
credentials never leave your machine.

It's built to pair with **[crow](https://maestro.press/software/crow-overview/)** —
a self‑hosted, [open‑source](https://github.com/kh0pper/crow) agentic framework and
MCP platform explicitly built for FERPA‑sensitive settings — so schools and other
privacy‑sensitive organizations can put AI to work on their own data **without
sending it to a third party** (see [Data privacy & FERPA](#data-privacy--ferpa)).
Because it speaks the open [Model Context Protocol](https://modelcontextprotocol.io),
it also works with any other MCP client (such as Claude Code or Claude Desktop) —
so you're never locked in.

> _Part of an effort to help school administrators adopt open‑source,
> FERPA‑compliant AI tools, paired with crow._

> **Who this guide is for.** It is written for non‑technical readers, including
> school administrators. You do **not** need to be a programmer. Where your
> access is limited (common in school districts where IT manages everything),
> the [What access do you have?](#what-access-do-you-have) section gives you a
> path — including an email you can send to your IT department.

---

## What it can do

**68 tools** across seven Google services:

| Service | What you can do | Tools |
|---|---|---|
| **Docs** | Read, search, and safely edit Google Docs (incl. comments) | 14 |
| **Slides** | Read and build Google Slides decks | 17 |
| **Gmail** | Search/read threads, draft replies, manage labels & filters | 11 |
| **Sheets** | Read (incl. formulas), write, append; create/rename/delete tabs; set cell formats | 8 |
| **Drive** | Search, list, organize, **copy**, rename, and trash files and folders | 9 |
| **Calendar** | List/read/create events, respond to invites | 5 |
| **Apps Script** | Read, edit, and push a project's script source; run functions | 4 |

**Safety is built in.** There is no "replace the whole document" tool (it has
destroyed formatting in the past); edits are surgical. The only tool that
actually *sends* email is restricted to an address list that is **empty by
default** — everything else creates **drafts** for you to review and send
yourself.

---

## What you'll need

- A Google account (a personal `@gmail.com` account, or a Google Workspace
  account from your school/organization).
- About **15 minutes**.
- **Python 3.11 or newer** on the computer that will run the server.
  (To check, open a terminal and run `python3 --version`.)

---

## What access do you have?

Setting this up requires creating a small "OAuth app" in the **Google Cloud
Console**. In many school districts, IT restricts who can do that. Take 30
seconds to find your tier, then follow the matching path.

> **Quick test:** Open [console.cloud.google.com](https://console.cloud.google.com)
> and sign in with the account you want to use. Can you create a **New Project**?
> Is the page blocked or missing options?

### Tier A — Full access (you can create a project)
You can do everything yourself. Follow **[Part 1](#part-1--set-up-google-cloud-tier-ab)**
and choose **Internal** on the consent screen. This is the best experience: your
sign‑in **never expires** and there is no "unverified app" warning.

### Tier B — You have the Console, but "Internal" is greyed out or scopes are blocked
Your project exists but your district restricts third‑party apps. Two options:
- Use **External** + add yourself as a **Test user** (Part 1 covers this). Note:
  External apps in "Testing" mode make you **re‑authorize about every 7 days**,
  and you'll see a "Google hasn't verified this app" screen (you can safely click
  through — see Part 1).
- **Better:** ask your IT/Workspace admin to mark the app **Trusted** so the
  warnings and limits go away. Send them the [email template](#email-to-send-your-it-department)
  with your OAuth client ID.
- Symptom check: an error like *"Access blocked: this app is blocked by your
  administrator"* means it's an admin policy, not something you can fix on the
  consent screen — use the email template.

### Tier C — No Google Cloud Console access at all
You can't create the app yourself, but you have options:
1. **Ask IT to create it for you.** Send the [email template](#email-to-send-your-it-department).
   They create one "Desktop" OAuth client and send you the `credentials.json`
   file (it is safe to email — it is not a password to your account).
2. **Try it first on a personal `@gmail.com` account** to learn how it works.
   A personal account has full access and lets you evaluate the tool. **Do not
   use a personal account for student records or other protected data** — see
   [Data privacy & FERPA](#data-privacy--ferpa).

### Tier D — Your district blocks third‑party apps entirely
This may not be possible on the work account without a policy change. You can
still evaluate the tool on a personal `@gmail.com` account (learning only, no
protected data), and share this page with IT to discuss a path forward.

### Email to send your IT department

> **Subject:** Request: OAuth client for a local Google Workspace tool
>
> Hi [IT team],
>
> I'd like to use a local, open‑source tool that lets an AI assistant help me
> with my own Google Workspace (Docs, Sheets, Slides, Gmail, Calendar). It runs
> on my own computer and uses Google's standard sign‑in — no data is sent to any
> third‑party server by the connector itself.
>
> Could you either:
> 1. Create an **OAuth client** of type **Desktop app** in a Google Cloud
>    project on our domain and send me the downloaded `credentials.json`, **or**
> 2. Mark my OAuth client ID **Trusted** under *Admin console → Security → API
>    controls → App access control* so it can use these Google APIs.
>
> It needs these APIs enabled: **Drive, Docs, Sheets, Slides, Gmail, Calendar,
> Apps Script**, with scopes for reading/editing my own Drive/Docs/Sheets/Slides,
> composing and managing my Gmail, managing my Calendar, and managing my own Apps
> Script projects.
>
> Thank you!

---

## Part 1 — Set up Google Cloud (Tier A/B)

Do this in your browser, signed in as the account you'll use.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create
   a **New Project** (any name, e.g. `workspace-mcp`).
2. **Enable the APIs.** Using the search bar at the top, find and **Enable** each
   of these (a few seconds each):
   **Google Drive API**, **Google Docs API**, **Google Sheets API**,
   **Google Slides API**, **Gmail API**, **Google Calendar API**,
   **Apps Script API**.
3. **Turn on the Apps Script API for your user** (only needed for the Apps Script
   tools). Visit [script.google.com/home/usersettings](https://script.google.com/home/usersettings)
   and switch **Google Apps Script API** to **On**. (This is a one‑time per‑user
   toggle, separate from enabling the API in the project above.)
4. **Configure the OAuth consent screen** (left menu → *APIs & Services → OAuth
   consent screen*, or *Google Auth Platform*).
   - **User type:** choose **Internal** if it's offered (best — non‑expiring,
     no warnings). If only **External** is available, pick it and add your own
     email as a **Test user**.
   - Fill in an app name and your email where asked.
5. **Create the credentials** (left menu → *Credentials* → *Create credentials*
   → *OAuth client ID*).
   - **Application type:** **Desktop app**. (This is important — it's what lets
     the local sign‑in work. Do **not** pick "Web application".)
   - Click **Create**, then **Download JSON**.

> **About the "Google hasn't verified this app" screen (External apps only):**
> Because the app is yours and unpublished, Google shows a warning. Click
> **Advanced → Go to [your app name] (unsafe)** — it's your own app, so it's
> safe. Internal apps don't show this. Also note External "Testing" apps allow
> up to **100 test users** and require re‑authorizing about **every 7 days**.

---

## Part 2 — Install the server

You need the project files on the machine that will run the server, and its
dependencies installed. The simplest way uses [`uv`](https://docs.astral.sh/uv/)
(a fast Python tool installer):

```bash
git clone https://github.com/kh0pper/google-workspace-mcp.git
cd google-workspace-mcp
uv sync
```

Prefer plain `pip`? From inside the cloned folder:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

---

## Part 3 — Sign in (authorize) — one time

1. Put the `credentials.json` you downloaded (or received from IT) here:
   - **macOS / Linux:** `~/.config/google-workspace-mcp/credentials.json`
   - (Or set the `GOOGLE_CREDENTIALS_FILE` environment variable to its location.)
2. Run the authorize command:

   ```bash
   uv run google-workspace-mcp-authorize
   ```

   Your browser opens; sign in and approve. Done — a token is saved next to your
   credentials and the server will reuse it automatically.

**On a remote server with no browser?** Use the copy‑paste flow:

```bash
uv run google-workspace-mcp-authorize --manual
```

It prints a link. Open it on any device, sign in, approve. Your browser then
tries to load a `http://localhost/?code=...` page that **won't open — that's
expected**. Copy the full address‑bar URL and paste it back into the terminal.

---

## Part 4 — Connect it to your AI (crow recommended)

The server speaks MCP over stdio, so it works with any MCP client. For a
**FERPA‑friendly, fully local** setup, pair it with **[crow](https://maestro.press/software/crow/)** —
a self‑hosted agentic framework and MCP platform. Run crow with a **local model**
(Ollama or any OpenAI‑compatible endpoint) and nothing leaves your network. You can
**install it in one click** from Crow's **Extensions** panel (it's in the
[official add‑on registry](https://github.com/kh0pper/crow-addons)), or connect it
as a standard MCP server using the configuration below — which also works in other
MCP clients (such as Claude Code or Claude Desktop).

A copy‑paste starting point is in [`.mcp.json.example`](./.mcp.json.example).

**MCP server configuration:**

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/google-workspace-mcp", "google-workspace-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/google-workspace-mcp` with the folder you cloned.
(If you installed it onto your PATH with `pipx install .` or `uv tool install .`,
you can use `"command": "google-workspace-mcp"` with no `args` instead.)

- **crow (recommended):** open Crow's **Extensions** panel and install **Google
  Workspace** in one click (or just ask your AI: *"Install the Google Workspace
  add-on"*), so the whole pipeline stays on your own hardware.
- **Claude Code:** add the block above to a `.mcp.json` in your project, or run
  `claude mcp add`. Restart and approve the server.
- **Other clients (Claude Desktop, etc.):** add the same server entry to that
  client's MCP config file.

---

## Data privacy & FERPA

**This matters if you handle student records or other protected data.**

This connector runs **locally** and only talks to Google with **your own**
sign‑in. But the document, email, or calendar content it retrieves is then
handed to **whatever AI model your client uses** — and *that choice* decides
whether data leaves your control:

- **Cloud / hosted AI models** (a hosted API) receive that content as part of
  their input. For student records, treat that as a disclosure to a third party
  that must be covered by your district's policies and data‑processing
  agreements **before** you use it.
- **Local / self‑hosted AI models** keep everything on your own computer or
  server — there is **no third‑party disclosure**, which is what makes a
  **FERPA‑compliant deployment possible**. **[crow](https://maestro.press/software/crow/)**
  is built for exactly this — a self‑hosted platform you pair with a local model
  ([Ollama](https://ollama.com) or any OpenAI‑compatible endpoint) so your data
  stays on infrastructure you control.

Keeping data local *enables* compliance; it does not by itself *guarantee* it
(access controls and your district's policies still apply). **Follow your
district policy and consult your privacy officer** before using this on
protected data.

---

## Tool reference (68 tools)

- **Docs (14):** `gdocs_read`, `gdocs_read_section`, `gdocs_get_structure`,
  `gdocs_find_replace`, `gdocs_append`, `gdocs_insert_at_heading`,
  `gdocs_replace_section`, `gdocs_create`, `gdocs_rewrite_passages`, plus
  comment tools (`gdocs_list_comments`, `gdocs_add_comment`, `gdocs_reply_comment`,
  `gdocs_resolve_comment`, `gdocs_apply_comment_edit`).
- **Slides (17):** read/structure/notes, create deck, add/duplicate/delete/reorder
  slides, add text boxes & images, format text/paragraphs, find‑replace, export.
- **Gmail (11):** `gmail_search_threads`, `gmail_get_thread`, `gmail_create_draft`,
  `gmail_create_threaded_reply`, `gmail_send_to_self`, `gmail_send_threaded_to_self`,
  `gmail_label_thread`, `gmail_archive`, `gmail_list_labels`, `gmail_create_label`,
  `gmail_create_filter`.
- **Drive (9):** `gdrive_search`, `gdrive_list_folder`, `gdrive_find_folder`,
  `gdrive_get_metadata`, `gdrive_create_folder`, `gdrive_move_file`,
  `gdrive_copy_file`, `gdrive_trash_file`, `gdrive_rename`.
- **Calendar (5):** `gcal_list_calendars`, `gcal_list_events`, `gcal_get_event`,
  `gcal_create_event`, `gcal_respond_to_event`.
- **Sheets (8):** `sheets_list`, `sheets_read` (incl. `value_render_option=FORMULA`),
  `sheets_write`, `sheets_append`, `sheets_add_tab`, `sheets_rename_tab`,
  `sheets_delete_tab`, `sheets_set_number_format`.
- **Apps Script (4):** `apps_script_get_content`, `apps_script_update_file`,
  `apps_script_update_content`, `apps_script_run`. Requires the Apps Script API
  enabled + the per‑user toggle at script.google.com/home/usersettings;
  `apps_script_run` also needs an API‑Executable deployment.

---

## Troubleshooting

- **"Access blocked / app blocked by your administrator":** a Workspace admin
  policy is blocking the app. Ask IT to mark it Trusted (see the email template).
- **"Google hasn't verified this app":** expected for your own External app —
  *Advanced → Go to [app] (unsafe)*. Avoid it entirely by using an Internal app.
- **Sign‑in expired after about a week:** you're on an External "Testing" app —
  publish it, or switch to an Internal app, to stop the 7‑day expiry.
- **"Not authenticated" when a tool runs:** run `google-workspace-mcp-authorize`
  again, or point `GOOGLE_TOKEN_FILE` at your token.
- **A scope was denied:** if you unchecked a permission during sign‑in, re‑run
  authorize and approve all requested permissions.

### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `~/.config/google-workspace-mcp/credentials.json` | Your downloaded OAuth client |
| `GOOGLE_TOKEN_FILE` | `~/.config/google-workspace-mcp/token.json` | Where your sign‑in token is stored |
| `GOOGLE_OAUTH_LOCAL_PORT` | `8090` | Local port used during browser sign‑in |
| `GMAIL_SEND_TO_SELF_ALLOWLIST` | *(empty)* | Comma‑separated addresses `gmail_send_to_self` may send to |

---

## Roadmap

- **One‑click crow extension — shipped.** Installable from Crow's **Extensions**
  panel via the [official add‑on registry](https://github.com/kh0pper/crow-addons).
- **Publish to PyPI** so `uvx google-workspace-mcp` works without the git URL.
- **Consulting:** crow plus tools like this are offered to help districts and
  administrators stand up open‑source, FERPA‑compliant AI on their own
  infrastructure.

## License

[MIT](./LICENSE) © Maestro Press. Free to use, modify, and distribute.
