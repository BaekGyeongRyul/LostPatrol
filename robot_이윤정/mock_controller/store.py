"""
store.py — 로봇 명령/상태를 저장하는 곳을 감싸는 "계약(contract)" 레이어.

.env 파일에 SUPABASE_URL / SUPABASE_KEY가 채워져 있으면 실제 Supabase를
쓰고, 없으면 로컬 JSON 파일을 대신 쓴다. 즉 .env.example을 .env로 복사해서
값만 채우면, controller.py나 send_command.py는 한 글자도 안 건드려도
자동으로 Supabase로 전환된다.

Supabase에 미리 만들어져 있어야 하는 테이블 (백경률 쪽에서 생성):

robot_commands
  id          : bigint, primary key, identity(자동증가)
  command     : text        예) "forward" | "backward" | "left" | "right"
                             | "stop" | "capture" | "buzz"
                             | "patrol_start" | "patrol_stop"
  status      : text        "pending" | "done"
  created_at  : timestamptz, default now()

robot_status  (딱 한 행만 사용, id=1 고정)
  id           : bigint, primary key   -- 항상 1
  state        : text        "idle" | "moving" | "stopped" | "camera_error" | "offline"
  last_command : text | null
  updated_at   : timestamptz  -- heartbeat. 5초마다 갱신, 15초 지나면 웹이 OFFLINE 표시
"""

import json
import os
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 아직 설치 안 됐으면 그냥 os.environ만 사용

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# anon(publishable) key로는 robot_commands/robot_status에 UPDATE 권한이 없다
# (팀 RLS 정책 확인됨) — 반드시 service_role key를 써야 한다.
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COMMANDS_FILE = os.path.join(DATA_DIR, "commands.json")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")

_STATUS_ROW_ID = 1  # robot_status 테이블은 이 id로 딱 한 행만 사용


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JSON 백엔드 (Supabase 없을 때)
# ---------------------------------------------------------------------------

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _init_json():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(COMMANDS_FILE):
        _write_json(COMMANDS_FILE, [])
    if not os.path.exists(STATUS_FILE):
        _write_json(
            STATUS_FILE,
            {"state": "idle", "last_command": None, "last_updated": _now_iso()},
        )


def _add_command_json(command: str) -> dict:
    commands = _read_json(COMMANDS_FILE, [])
    new_id = (max((c["id"] for c in commands), default=0)) + 1
    record = {
        "id": new_id,
        "command": command,
        "status": "pending",
        "created_at": _now_iso(),
        "executed_at": None,
    }
    commands.append(record)
    _write_json(COMMANDS_FILE, commands)
    return record


def _get_pending_commands_json() -> list:
    commands = _read_json(COMMANDS_FILE, [])
    pending = [c for c in commands if c["status"] == "pending"]
    return sorted(pending, key=lambda c: c["id"])


def _mark_command_done_json(command_id: int) -> None:
    commands = _read_json(COMMANDS_FILE, [])
    for c in commands:
        if c["id"] == command_id:
            c["status"] = "done"
            c["executed_at"] = _now_iso()
    _write_json(COMMANDS_FILE, commands)


def _get_status_json() -> dict:
    return _read_json(
        STATUS_FILE,
        {"state": "idle", "last_command": None, "updated_at": _now_iso()},
    )


def _update_status_json(state: str, last_command: str = None) -> dict:
    status = {
        "state": state,
        "last_command": last_command,
        "updated_at": _now_iso(),
    }
    _write_json(STATUS_FILE, status)
    return status


# ---------------------------------------------------------------------------
# Supabase 백엔드
# ---------------------------------------------------------------------------

_supabase_client = None


def _sb():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client  # 여기서만 import 해서, 패키지 없어도
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)  # JSON 모드는 안 깨지게
    return _supabase_client


def _init_supabase():
    # 테이블 자체는 백경률이 Supabase 대시보드에서 미리 만들어둔다.
    # 여기서는 robot_status의 기준 행(id=1)이 없으면 하나 만들어준다.
    existing = (
        _sb().table("robot_status").select("id").eq("id", _STATUS_ROW_ID).execute()
    )
    if not existing.data:
        _update_status_supabase(state="idle", last_command=None)


def _add_command_supabase(command: str) -> dict:
    result = (
        _sb()
        .table("robot_commands")
        .insert({"command": command, "status": "pending"})
        .execute()
    )
    return result.data[0]


def _get_pending_commands_supabase() -> list:
    result = (
        _sb()
        .table("robot_commands")
        .select("*")
        .eq("status", "pending")
        .order("id")
        .execute()
    )
    return result.data


def _mark_command_done_supabase(command_id: int) -> None:
    _sb().table("robot_commands").update(
        {"status": "done", "executed_at": _now_iso()}
    ).eq("id", command_id).execute()


def _get_status_supabase() -> dict:
    result = (
        _sb()
        .table("robot_status")
        .select("*")
        .eq("id", _STATUS_ROW_ID)
        .execute()
    )
    if result.data:
        return result.data[0]
    return {"state": "idle", "last_command": None, "updated_at": _now_iso()}


def _update_status_supabase(state: str, last_command: str = None) -> dict:
    row = {
        "id": _STATUS_ROW_ID,
        "state": state,
        "last_command": last_command,
        "updated_at": _now_iso(),
    }
    _sb().table("robot_status").upsert(row).execute()
    return row


# ---------------------------------------------------------------------------
# 공개 API — controller.py / send_command.py는 이 함수들만 사용한다.
# 백엔드가 JSON이든 Supabase든 여기서부터는 완전히 동일하게 동작한다.
# ---------------------------------------------------------------------------

def init_store():
    if USE_SUPABASE:
        print(f"[store] Supabase 백엔드 사용 중 ({SUPABASE_URL})")
        _init_supabase()
    else:
        print("[store] 로컬 JSON 백엔드 사용 중 (.env에 SUPABASE_URL/KEY 채우면 자동 전환)")
        _init_json()


def add_command(command: str) -> dict:
    return _add_command_supabase(command) if USE_SUPABASE else _add_command_json(command)


def get_pending_commands() -> list:
    return _get_pending_commands_supabase() if USE_SUPABASE else _get_pending_commands_json()


def mark_command_done(command_id: int) -> None:
    if USE_SUPABASE:
        _mark_command_done_supabase(command_id)
    else:
        _mark_command_done_json(command_id)


def get_status() -> dict:
    return _get_status_supabase() if USE_SUPABASE else _get_status_json()


def update_status(state: str, last_command: str = None) -> dict:
    if USE_SUPABASE:
        return _update_status_supabase(state, last_command)
    return _update_status_json(state, last_command)
