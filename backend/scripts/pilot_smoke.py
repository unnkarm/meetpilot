"""Manually check the available Pilot text endpoints against a local backend.

Set MEETPILOT_TOKEN to a valid Clerk bearer token. Task creation is opt-in.
"""

import argparse
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(base_url: str, path: str, token: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                 **({"Content-Type": "application/json"} if body is not None else {})},
        method="POST" if body is not None else "GET",
    )
    with urlopen(request, timeout=240) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test Pilot context, cited Q&A, and optional task action")
    parser.add_argument("--meeting-id", type=uuid.UUID, required=True)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--question", default="What did we just agree on?")
    parser.add_argument("--skip-question", action="store_true")
    parser.add_argument("--action", help="Explicit Hey Pilot task command; creates a real task when supplied")
    args = parser.parse_args()
    token = os.getenv("MEETPILOT_TOKEN", "").strip()
    if not token:
        parser.error("Set MEETPILOT_TOKEN to a valid Clerk bearer token")
    path = f"/api/v1/meetings/{args.meeting_id}/pilot"
    try:
        context = request_json(args.api_base, path + "/context", token)
        print(json.dumps({
            "meeting_id": context["meeting_id"],
            "language_code": context.get("language_code"),
            "active_speakers": context.get("active_speakers", []),
            "recent_segment_count": len(context.get("recent_segments", [])),
            "recent_task_count": len(context.get("recent_tasks", [])),
            "recent_decision_count": len(context.get("recent_decisions", [])),
            "recent_memory_count": len(context.get("recent_memory", [])),
        }, ensure_ascii=False, indent=2))
        if not args.skip_question:
            answer = request_json(args.api_base, path + "/ask", token, {"question": args.question})
            print(json.dumps(answer, ensure_ascii=False, indent=2))
        if args.action:
            task = request_json(args.api_base, path + "/action", token, {"command": args.action})
            print(json.dumps({"created_task_id": task["id"], "title": task["title"],
                              "assignee_name": task.get("assignee_name")}, ensure_ascii=False, indent=2))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Pilot API returned HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, KeyError, ValueError) as exc:
        print(f"Pilot smoke check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
