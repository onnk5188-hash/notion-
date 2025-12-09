from __future__ import annotations
import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

STATE_FILE = Path(".notion_timer_state.json")
NOTION_VERSION = "2022-06-28"


@dataclass
class SessionState:
    project: str
    task: str
    start: str  # ISO timestamp

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        return cls(project=data["project"], task=data["task"], start=data["start"])

    def to_dict(self) -> Dict[str, Any]:
        return {"project": self.project, "task": self.task, "start": self.start}


def _read_state() -> Optional[SessionState]:
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
        return SessionState.from_dict(data)
    except Exception:
        return None


def _write_state(state: SessionState) -> None:
    STATE_FILE.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))


def _clear_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).astimezone().isoformat()


def _parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


def _ensure_env(value: Optional[str], name: str) -> str:
    if value:
        return value
    env_val = os.getenv(name)
    if not env_val:
        raise SystemExit(f"Missing required {name}. Provide it via environment variable or CLI flag.")
    return env_val


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8")
    except error.HTTPError as exc:  # type: ignore[assignment]
        status = exc.code
        text = exc.read().decode("utf-8")
    except error.URLError as exc:  # type: ignore[assignment]
        raise SystemExit(f"Network error calling Notion: {exc}")

    if status >= 400:
        raise SystemExit(
            f"Notion API error {status}: {text}. Verify database permissions and property names."
        )


def create_notion_page(
    token: str,
    database_id: str,
    project: str,
    task: str,
    start_iso: str,
    end_iso: str,
    duration_minutes: float,
) -> None:
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": {
            "Task": {"title": [{"text": {"content": task}}]},
            "Project": {"select": {"name": project}},
            "Start": {"date": {"start": start_iso}},
            "End": {"date": {"start": end_iso}},
            "Duration (minutes)": {"number": round(duration_minutes, 2)},
        },
    }
    _post_json(url, headers, payload)


def start_session(args: argparse.Namespace) -> None:
    if _read_state() is not None:
        raise SystemExit("A session is already running. Use 'stop' before starting a new one.")

    start_time = _iso_now()
    state = SessionState(project=args.project, task=args.task, start=start_time)
    _write_state(state)
    print(f"Started '{state.project}' / '{state.task}' at {state.start}")


def stop_session(args: argparse.Namespace) -> None:
    state = _read_state()
    if state is None:
        raise SystemExit("No active session found. Use 'start' first.")

    token = _ensure_env(args.token, "NOTION_TOKEN")
    database_id = _ensure_env(args.database_id, "NOTION_DATABASE_ID")
    end_time = _iso_now()

    start_dt = _parse_iso(state.start)
    end_dt = _parse_iso(end_time)
    duration_minutes = (end_dt - start_dt).total_seconds() / 60

    create_notion_page(
        token=token,
        database_id=database_id,
        project=state.project,
        task=state.task,
        start_iso=state.start,
        end_iso=end_time,
        duration_minutes=duration_minutes,
    )

    _clear_state()
    print(
        f"Recorded '{state.project}' / '{state.task}' for {duration_minutes:.2f} minutes."
        " Entry stored in Notion."
    )


def status_session(_: argparse.Namespace) -> None:
    state = _read_state()
    if state is None:
        print("No active session.")
        return
    print(f"Running: project='{state.project}', task='{state.task}', started at {state.start}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Minimal Notion-backed timer. Start a session, then stop it to send the elapsed "
            "time into your Notion database."
        )
    )
    parser.add_argument(
        "--token",
        help="Notion integration token. If omitted, the NOTION_TOKEN environment variable is used.",
    )
    parser.add_argument(
        "--database-id",
        help=(
            "Notion database ID that will receive time entries. If omitted, "
            "NOTION_DATABASE_ID environment variable is used."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Begin a new timer session")
    start_parser.add_argument("project", help="Project or category name (maps to Notion select)")
    start_parser.add_argument("task", help="Specific task name (maps to Notion title)")
    start_parser.set_defaults(func=start_session)

    stop_parser = subparsers.add_parser("stop", help="Stop the timer and write to Notion")
    stop_parser.set_defaults(func=stop_session)

    status_parser = subparsers.add_parser("status", help="Show the current timer state")
    status_parser.set_defaults(func=status_session)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
