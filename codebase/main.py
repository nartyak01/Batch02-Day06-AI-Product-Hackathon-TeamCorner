from __future__ import annotations

import json
import os
import sys
import traceback

from vinmec_agent import run_agent_turn
from vinmec_agent.domain.constants import STATE_ERROR
from vinmec_agent.domain.response import base_response


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _load_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def cli_main() -> int:
    _configure_stdio()
    _load_env_file()
    try:
        raw = sys.stdin.read().strip()
        if raw:
            payload = json.loads(raw)
        elif len(sys.argv) > 1:
            payload = {"user_message": " ".join(sys.argv[1:]), "history": [], "context": {}}
        else:
            payload = {"user_message": "", "history": [], "context": {}}

        result = run_agent_turn(
            user_message=payload.get("user_message") or payload.get("message") or "",
            history=payload.get("history") or [],
            context=payload.get("context") or {},
        )
    except Exception as exc:  # pragma: no cover - CLI safety
        if os.getenv("AGENT_DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        result = base_response(
            reply="Hệ thống agent đang gặp lỗi. Vui lòng thử lại hoặc chuyển sang callback.",
            state=STATE_ERROR,
            needs_more_info=False,
            meta={"error": exc.__class__.__name__},
        )

    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
