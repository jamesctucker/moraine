#!/usr/bin/env python3
"""Allocate the next sequential artifact number, safe under concurrent sessions.

Artifacts are numbered `NN-slug.md` in `artifacts/`. Two sessions running at
once can both read the directory and compute the same "next" number before
either writes a file — that collision happened on 2026-10-02 (two sessions
claimed 35). `--claim` prevents it by creating the file exclusively (O_EXCL)
and retrying the next number on a collision.

Usage:
    python scripts/workspace/next-artifact.py
    python scripts/workspace/next-artifact.py --claim spec-hardening-review
    python scripts/workspace/next-artifact.py --claim pan-review --title "Panorama PR review"
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from lib import WORKSPACE

ARTIFACTS = WORKSPACE / "artifacts"
TEMPLATE = ARTIFACTS / "_TEMPLATE.md"
NUMBERED = re.compile(r"^(\d+)-")


def highest_number() -> int:
    highest = 0
    for path in ARTIFACTS.glob("*"):
        match = NUMBERED.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise SystemExit("error: slug has no usable characters")
    return slug


def render(title: str, context: str) -> str:
    if not TEMPLATE.exists():
        raise SystemExit(f"error: template not found at {TEMPLATE}")
    text = TEMPLATE.read_text()
    text = re.sub(r"^# .*$", f"# {title}", text, count=1, flags=re.MULTILINE)
    text = text.replace("> **Date:** YYYY-MM-DD", f"> **Date:** {date.today().isoformat()}")
    if context:
        text = text.replace("> **Context:** Why this artifact was produced.", f"> **Context:** {context}")
    return text


def claim(slug: str, title: str, context: str) -> Path:
    number = highest_number() + 1
    while True:
        path = ARTIFACTS / f"{number:02d}-{slug}.md"
        try:
            with open(path, "x") as handle:
                handle.write(render(title, context))
            return path
        except FileExistsError:
            number += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Allocate the next artifact number.")
    parser.add_argument("--claim", metavar="SLUG", help="create NN-SLUG.md from the template")
    parser.add_argument("--title", default="Title", help="document title (default: Title)")
    parser.add_argument("--context", default="", help="one-line context for the header")
    args = parser.parse_args()

    if args.claim:
        path = claim(slugify(args.claim), args.title, args.context)
        rel = path.relative_to(WORKSPACE)
        print(f"created {rel}")
        return 0

    print(f"{highest_number() + 1:02d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
