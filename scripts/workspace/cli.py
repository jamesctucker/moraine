"""The `moraine` command line: sync, and packs list/enable/disable."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import WORKSPACE
from manifest import (
    LOCAL_PACK,
    MANIFEST_NAME,
    ManifestError,
    enabled_packs,
    harness_fits,
    load_manifests,
    local_pack,
    missing_prereqs,
    pack_skills,
    write_manifest,
)
from sync import SyncError, SyncPlan, run

# Longer change lists are summarised; the plan is the same either way.
MAX_SHOWN = 12


def main(argv: list[str], workspace: Path = WORKSPACE) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args, workspace)
    except (ManifestError, SyncError) as e:
        for problem in e.problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moraine", description="Make the workspace match moraine.yaml.")
    commands = parser.add_subparsers(dest="command", required=True)

    sync = commands.add_parser("sync", help="link enabled pack skills; write MCP servers and the cron job list")
    sync.add_argument("--dry-run", action="store_true", help="show what would change")
    sync.set_defaults(handler=cmd_sync)

    packs = commands.add_parser("packs", help="inspect and change the enabled packs")
    verbs = packs.add_subparsers(dest="verb", required=True)
    verbs.add_parser("list", help="every pack: enabled, prerequisites, harness fit").set_defaults(handler=cmd_packs_list)
    for verb, helptext in (
        ("enable", "add a pack to moraine.yaml, then sync"),
        ("disable", "remove a pack from moraine.yaml, then sync"),
    ):
        command = verbs.add_parser(verb, help=helptext)
        command.add_argument("name", help="pack name")
        command.set_defaults(handler=cmd_packs_enable if verb == "enable" else cmd_packs_disable)
    return parser


# ── sync ────────────────────────────────────────────────────────────


def cmd_sync(args: argparse.Namespace, workspace: Path) -> int:
    return _sync(workspace, args.dry_run)


def print_report(result: SyncPlan, dry_run: bool) -> None:
    prefix = "would " if dry_run else ""
    for line in result.packs:
        print(f"  {line}")
    if not result.packs:
        print("  no packs enabled (core only); see: moraine packs list")
    for change in result.changes[:MAX_SHOWN]:
        print(f"  {prefix}{change.detail}")
    if len(result.changes) > MAX_SHOWN:
        print(f"  {prefix}… and {len(result.changes) - MAX_SHOWN} more")
    if not result.changes:
        print(f"  {'nothing to change' if dry_run else 'already in sync'}")
    for note in result.notes:
        print(f"  note: {note}")


def _sync(workspace: Path, dry_run: bool = False) -> int:
    print_report(run(workspace, dry_run=dry_run), dry_run)
    return 0


# ── packs list ──────────────────────────────────────────────────────


def cmd_packs_list(args: argparse.Namespace, workspace: Path) -> int:
    manifest, packs = load_manifests(workspace)
    enabled = set(enabled_packs(manifest.packs, packs))
    print(f"{'PACK':<13}{'ENABLED':<10}{'SKILLS':<8}{'PREREQS':<24}HARNESS")
    for pack in [local_pack(workspace), *packs.values()]:
        state = "always" if pack.name == LOCAL_PACK else "yes" if pack.name in enabled else "no"
        missing = [prereq.cmd for prereq in missing_prereqs(pack)]
        prereqs = f"missing: {', '.join(missing)}" if missing else "ok"
        harness = ", ".join(pack.harnesses)
        if not harness_fits(pack, manifest.harnesses):
            harness += " (not listed for this workspace)"
        print(f"{pack.name:<13}{state:<10}{len(pack_skills(pack)):<8}{prereqs:<24}{harness}")
        print(f"{'':<13}{pack.description}")
    return 0


# ── packs enable / disable ─────────────────────────────────────────


def cmd_packs_enable(args: argparse.Namespace, workspace: Path) -> int:
    manifest, packs = load_manifests(workspace)
    name = args.name
    if name == LOCAL_PACK:
        print(f"'{LOCAL_PACK}' is always enabled and is never listed in {MANIFEST_NAME}.")
        return 1
    if name not in packs:
        print(f"no pack '{name}'. Available: {', '.join([LOCAL_PACK, *packs])}")
        return 1

    wanted = enabled_packs((name,), packs)
    unfitted = [pack for pack in wanted.values() if not harness_fits(pack, manifest.harnesses)]
    if unfitted:
        needed = ", ".join(sorted({harness for pack in unfitted for harness in pack.harnesses if harness != "any"}))
        print(f"'{'/'.join(pack.name for pack in unfitted)}' needs the {needed} harness. Add it in {MANIFEST_NAME}:")
        print(f"  harnesses: [{needed}]")
        return 1
    write_manifest(workspace / MANIFEST_NAME, packs=sorted({*manifest.packs, *wanted}))
    return _sync(workspace)


def cmd_packs_disable(args: argparse.Namespace, workspace: Path) -> int:
    manifest, packs = load_manifests(workspace)
    name = args.name
    if name == LOCAL_PACK:
        print(f"'{LOCAL_PACK}' is always enabled and is never listed in {MANIFEST_NAME}.")
        return 1
    if name not in manifest.packs:
        print(f"'{name}' is not listed in {MANIFEST_NAME}.")
        return 1

    dependent = [pack.name for pack in enabled_packs(manifest.packs, packs).values() if name in pack.requires]
    if dependent:
        print(f"refusing: '{name}' is required by {', '.join(dependent)}. Disable those first.")
        return 1
    write_manifest(workspace / MANIFEST_NAME, packs=[pack for pack in manifest.packs if pack != name])
    return _sync(workspace)
