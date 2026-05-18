import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.app.api.agents import agent_manifest
from backend.app.schemas import Preset, RunRequest
from backend.app.storage import conversation_repo, preset_repo


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _print_json(value: Any) -> None:
    print(json.dumps(_jsonable(value), ensure_ascii=False, indent=2))


def _load_preset(args: argparse.Namespace) -> Preset:
    if args.preset_id:
        preset = preset_repo.get_preset(args.preset_id)
        if preset is None:
            raise SystemExit(f"preset not found: {args.preset_id}")
        return preset

    path = Path(args.preset_file).expanduser()
    try:
        return Preset.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid preset file: {path}: {exc}") from exc


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise SystemExit("provide --prompt or pipe prompt text on stdin")


def _max_turns(value: str) -> int:
    try:
        turns = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("max turns must be an integer") from exc
    if turns < 1 or turns > 50:
        raise argparse.ArgumentTypeError("max turns must be between 1 and 50")
    return turns


async def _run(args: argparse.Namespace) -> None:
    from backend.app.orchestration.runner import run_conversation_to_completion

    preset = _load_preset(args)
    if args.max_turns is not None:
        preset = preset.model_copy(update={"max_turns": args.max_turns})

    response = await run_conversation_to_completion(
        RunRequest(
            preset=preset,
            prompt=_read_prompt(args),
            conversation_id=args.conversation_id,
        )
    )
    if args.format == "text":
        for message in response.new_messages:
            if message.role == "assistant":
                print(f"{message.name}: {message.content}")
        return
    _print_json(response)


def _show_conversation(args: argparse.Namespace) -> None:
    conversation = conversation_repo.get_conversation(args.conversation_id)
    if conversation is None:
        raise SystemExit(f"conversation not found: {args.conversation_id}")
    if args.format == "text":
        for message in conversation.messages:
            print(f"{message.name}: {message.content}")
        return
    _print_json(conversation)


async def _manifest() -> None:
    _print_json(await agent_manifest())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.app.cli",
        description="Agent-friendly CLI for agent-room presets and conversations.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("manifest", help="Print machine-readable agent capabilities.")
    subcommands.add_parser("presets", help="List saved presets as JSON.")
    subcommands.add_parser("conversations", help="List saved conversations as JSON.")

    show = subcommands.add_parser("show-conversation", help="Print a saved conversation.")
    show.add_argument("conversation_id")
    show.add_argument("--format", choices=["json", "text"], default="json")

    run = subcommands.add_parser("run", help="Run a preset to completion.")
    preset_source = run.add_mutually_exclusive_group(required=True)
    preset_source.add_argument("--preset-id")
    preset_source.add_argument("--preset-file")
    run.add_argument("--prompt")
    run.add_argument("--conversation-id")
    run.add_argument("--max-turns", type=_max_turns)
    run.add_argument("--format", choices=["json", "text"], default="json")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "manifest":
        asyncio.run(_manifest())
    elif args.command == "presets":
        _print_json(preset_repo.list_presets())
    elif args.command == "conversations":
        _print_json(conversation_repo.list_conversations())
    elif args.command == "show-conversation":
        _show_conversation(args)
    elif args.command == "run":
        asyncio.run(_run(args))
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
