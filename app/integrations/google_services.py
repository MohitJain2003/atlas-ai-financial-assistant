"""
Google OAuth2 Integration — Calendar, Gmail, Drive, Sheets.
Users connect their Google account by visiting a Telegram-provided link.
Tokens are stored per-user in the database (JSON column).
"""
import logging
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


def get_google_credentials():
    """Load Google OAuth client credentials from environment."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    return client_id, client_secret


def is_google_configured() -> bool:
    """Check if Google OAuth credentials are set."""
    client_id, client_secret = get_google_credentials()
    return bool(client_id and client_secret)


def get_auth_url(telegram_id: int) -> str:
    """Generate Google OAuth authorization URL for this user."""
    from google_auth_oauthlib.flow import Flow
    client_id, client_secret = get_google_credentials()

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(telegram_id),
        prompt="consent",
    )
    return auth_url


def exchange_code_for_tokens(code: str, state: str) -> Optional[Dict]:
    """Exchange OAuth code for access + refresh tokens."""
    try:
        from google_auth_oauthlib.flow import Flow
        client_id, client_secret = get_google_credentials()

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
        flow.redirect_uri = REDIRECT_URI
        flow.fetch_token(code=code)

        creds = flow.credentials
        return {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else [],
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return None


def build_service_from_tokens(service_name: str, version: str, token_data: dict):
    """Build a Google API service client from stored token data."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", []),
    )
    return build(service_name, version, credentials=creds)


class GoogleCalendarService:
    """Google Calendar integration — read events, create meetings, set reminders."""

    def get_upcoming_events(self, token_data: dict, days: int = 7) -> List[Dict]:
        """Fetch upcoming calendar events for the next N days."""
        try:
            service = build_service_from_tokens("calendar", "v3", token_data)
            now = datetime.utcnow().isoformat() + "Z"
            end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=end,
                maxResults=15,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            return [
                {
                    "summary": e.get("summary", "No Title"),
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "location": e.get("location", ""),
                    "description": (e.get("description", "") or "")[:200],
                }
                for e in events
            ]
        except Exception as e:
            logger.error(f"Calendar fetch error: {e}")
            return []

    def create_event(self, token_data: dict, summary: str, start_dt: str,
                     end_dt: str, description: str = "") -> Dict:
        """Create a calendar event."""
        try:
            service = build_service_from_tokens("calendar", "v3", token_data)
            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_dt, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_dt, "timeZone": "Asia/Kolkata"},
            }
            created = service.events().insert(calendarId="primary", body=event).execute()
            return {"status": "created", "event_id": created.get("id"), "link": created.get("htmlLink")}
        except Exception as e:
            logger.error(f"Calendar create event error: {e}")
            return {"error": str(e)}


class GmailService:
    """Gmail integration — search emails, summarize threads about a company."""

    def search_emails(self, token_data: dict, query: str, max_results: int = 5) -> List[Dict]:
        """Search emails and return subject + snippet."""
        try:
            service = build_service_from_tokens("gmail", "v1", token_data)
            results = service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            emails = []
            for msg in messages[:max_results]:
                full = service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]
                ).execute()

                headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
                emails.append({
                    "subject": headers.get("Subject", "No Subject"),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "snippet": full.get("snippet", ""),
                })
            return emails
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return []


class GoogleSheetsService:
    """Google Sheets integration — read spreadsheet data for analysis."""

    def read_sheet(self, token_data: dict, spreadsheet_id: str, range_name: str = "A1:Z100") -> Dict:
        """Read data from a Google Sheet."""
        try:
            service = build_service_from_tokens("sheets", "v4", token_data)
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()

            values = result.get("values", [])
            if not values:
                return {"data": [], "error": "Sheet is empty."}

            headers = values[0] if values else []
            rows = []
            for row in values[1:20]:  # Max 20 rows for AI context
                row_dict = {}
                for i, cell in enumerate(row):
                    col_name = headers[i] if i < len(headers) else f"Col{i}"
                    row_dict[col_name] = cell
                rows.append(row_dict)

            return {"headers": headers, "data": rows, "total_rows": len(values) - 1}
        except Exception as e:
            logger.error(f"Sheets read error: {e}")
            return {"error": str(e)}
