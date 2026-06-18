"""
Centralized Google OAuth2 authentication.

Credential and token paths are configurable via environment variables and
default to ~/.config/google-workspace-mcp/. Token writes use atomic rename to
prevent corruption from concurrent processes.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Scopes covering Drive, Docs, Sheets, Slides, Gmail, and Calendar. Adding or
# removing a scope invalidates existing tokens — re-run the authorize flow once
# per credentials directory after any change here.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    # Apps Script API: read/edit/push project .gs source (projects.getContent /
    # updateContent) and scripts.run. Requires the Apps Script API enabled in the
    # OAuth client's GCP project AND the user's Apps Script API setting
    # (script.google.com/home/usersettings) turned on.
    "https://www.googleapis.com/auth/script.projects",
]

# Default credential paths, overridable via env vars:
#   GOOGLE_CREDENTIALS_FILE — the OAuth client secret downloaded from Google Cloud
#   GOOGLE_TOKEN_FILE       — where the user's OAuth token is stored after authorizing
_DEFAULT_CONFIG_DIR = Path.home() / ".config" / "google-workspace-mcp"
DEFAULT_CREDENTIALS_FILE = _DEFAULT_CONFIG_DIR / "credentials.json"
DEFAULT_TOKEN_FILE = _DEFAULT_CONFIG_DIR / "token.json"


def _get_credentials_file() -> Path:
    return Path(os.environ.get("GOOGLE_CREDENTIALS_FILE", str(DEFAULT_CREDENTIALS_FILE)))


def _get_token_file() -> Path:
    return Path(os.environ.get("GOOGLE_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))


class GoogleAuth:
    """Manages Google OAuth2 credentials with atomic token persistence."""

    def __init__(
        self,
        credentials_file: Optional[Path] = None,
        token_file: Optional[Path] = None,
    ):
        self.credentials_file = credentials_file or _get_credentials_file()
        self.token_file = token_file or _get_token_file()
        self._credentials: Optional[Credentials] = None

    @property
    def credentials(self) -> Optional[Credentials]:
        """Get current credentials, loading/refreshing as needed."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Load from token file
        if self.token_file.exists():
            try:
                self._credentials = Credentials.from_authorized_user_file(
                    str(self.token_file), SCOPES
                )
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")

        # Refresh if expired
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
                logger.info("Refreshed expired credentials")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                self._credentials = None

        return self._credentials

    def is_authenticated(self) -> bool:
        creds = self.credentials
        return creds is not None and creds.valid

    def _save_credentials(self):
        """Save credentials atomically (write to temp + rename)."""
        if not self._credentials:
            return
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file in same directory, then rename
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.token_file.parent), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(self._credentials.to_json())
                os.rename(tmp_path, str(self.token_file))
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            logger.info(f"Saved credentials to {self.token_file}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def authorize(self) -> bool:
        """Run the interactive OAuth2 flow (only needed once).

        Tries a local browser flow first; if that fails (e.g. headless machine),
        falls back to printing a URL and reading the redirect code you paste back.
        For a friendlier experience, use the ``google-workspace-mcp-authorize``
        command, which supports an explicit ``--manual`` copy-paste mode.
        """
        if not self.credentials_file.exists():
            logger.error(f"Credentials file not found: {self.credentials_file}")
            return False
        # Google deprecated the out-of-band (oob) redirect; use a localhost
        # redirect, which installed/Desktop OAuth clients accept on any port.
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                SCOPES,
                redirect_uri="http://localhost",
            )
            try:
                local_port = int(os.environ.get("GOOGLE_OAUTH_LOCAL_PORT", "8090"))
                self._credentials = flow.run_local_server(
                    port=local_port, open_browser=True,
                    prompt="consent", access_type="offline",
                )
            except Exception:
                auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
                print(f"\nOpen this URL in your browser and sign in:\n{auth_url}\n")
                print(
                    "Your browser will try to load a 'http://localhost/?code=...' page "
                    "that won't open — that's expected. Copy the full address-bar URL "
                    "(or just the code) and paste it here."
                )
                pasted = input("Paste the redirect URL or code: ").strip()
                code = pasted
                if "code=" in pasted:
                    import urllib.parse
                    code = urllib.parse.parse_qs(
                        urllib.parse.urlparse(pasted).query
                    ).get("code", [pasted])[0]
                flow.fetch_token(code=code)
                self._credentials = flow.credentials

            self._save_credentials()
            return True
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            return False


# --- Service singletons (lazy) ---

_auth: Optional[GoogleAuth] = None
_drive_service = None
_docs_service = None
_gmail_service = None
_sheets_service = None
_calendar_service = None
_slides_service = None
_script_service = None

_NOT_AUTHED_HINT = (
    "Not authenticated. Run `google-workspace-mcp-authorize` to sign in "
    "(or point GOOGLE_TOKEN_FILE at an existing token)."
)


def get_auth() -> GoogleAuth:
    global _auth
    if _auth is None:
        _auth = GoogleAuth()
    return _auth


def get_drive_service():
    """Get or create Drive API v3 service."""
    global _drive_service
    if _drive_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _drive_service = build("drive", "v3", credentials=auth.credentials)
    return _drive_service


def get_docs_service():
    """Get or create Google Docs API v1 service."""
    global _docs_service
    if _docs_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _docs_service = build("docs", "v1", credentials=auth.credentials)
    return _docs_service


def get_gmail_service():
    """Get or create Gmail API v1 service."""
    global _gmail_service
    if _gmail_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _gmail_service = build("gmail", "v1", credentials=auth.credentials)
    return _gmail_service


def get_sheets_service():
    """Get or create Google Sheets API v4 service."""
    global _sheets_service
    if _sheets_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _sheets_service = build("sheets", "v4", credentials=auth.credentials)
    return _sheets_service


def get_slides_service():
    """Get or create Google Slides API v1 service."""
    global _slides_service
    if _slides_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _slides_service = build("slides", "v1", credentials=auth.credentials)
    return _slides_service


def get_calendar_service():
    """Get or create Calendar API v3 service."""
    global _calendar_service
    if _calendar_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _calendar_service = build("calendar", "v3", credentials=auth.credentials)
    return _calendar_service


def get_script_service():
    """Get or create Apps Script API v1 service."""
    global _script_service
    if _script_service is None:
        auth = get_auth()
        if not auth.is_authenticated():
            raise RuntimeError(_NOT_AUTHED_HINT)
        _script_service = build("script", "v1", credentials=auth.credentials)
    return _script_service


def refresh_services():
    """Force re-creation of services (after token refresh on 401)."""
    global _drive_service, _docs_service, _gmail_service, _sheets_service
    global _calendar_service, _slides_service, _script_service
    auth = get_auth()
    if auth._credentials and auth._credentials.expired and auth._credentials.refresh_token:
        auth._credentials.refresh(Request())
        auth._save_credentials()
    _drive_service = None
    _docs_service = None
    _gmail_service = None
    _sheets_service = None
    _calendar_service = None
    _slides_service = None
    _script_service = None
