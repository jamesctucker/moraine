"""Frontmatter parser — one implementation, two interface entry points.

The common caller just wants the dict and body:

    fm, body = parse(content)

The validator wants to distinguish absence from breakage:

    result = parse_detailed(content)
    if result.error:
        report(result.error)

Design notes:
- Absence is NOT an error. A file with no "---" returns (None, content), error=None.
- Breakage IS an error. Malformed delimiters, invalid YAML, or non-mapping
  content all set the error field — but body is still extracted when the
  delimiter pair is valid, so callers aren't penalised.
- Delimiters are line-anchored: "---" must sit on its own line (trailing
  whitespace allowed), so scalars containing "---" and body horizontal rules
  survive intact.
- No file I/O, no rel_path parameter, no side effects. Pure str -> data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import yaml

# A delimiter is a line that is exactly three dashes (trailing whitespace/CR
# tolerated) — not a longer rule, not text on the same line.
_DELIMITER_LINE_RE = re.compile(r"^---[ \t]*\r?$")


class ParseErrorKind(Enum):
    MALFORMED_DELIMITER = auto()
    INVALID_YAML = auto()
    NOT_A_MAPPING = auto()


@dataclass(frozen=True)
class ParseError:
    kind: ParseErrorKind
    detail: str
    line: int | None = None


@dataclass(frozen=True)
class ParseResult:
    frontmatter: dict[str, Any] | None
    body: str
    error: ParseError | None

    @property
    def ok(self) -> bool:
        return self.error is None


def _load_frontmatter(raw: str, body: str) -> ParseResult:
    try:
        fm = yaml.safe_load(raw)
    except yaml.MarkedYAMLError as e:
        line = e.problem_mark.line + 1 if e.problem_mark else None
        return ParseResult(
            frontmatter=None,
            body=body,
            error=ParseError(kind=ParseErrorKind.INVALID_YAML, detail=str(e).strip(), line=line),
        )
    except yaml.YAMLError as e:
        return ParseResult(
            frontmatter=None,
            body=body,
            error=ParseError(kind=ParseErrorKind.INVALID_YAML, detail=str(e).strip()),
        )

    if not isinstance(fm, dict):
        type_name = type(fm).__name__ if fm is not None else "empty"
        return ParseResult(
            frontmatter=None,
            body=body,
            error=ParseError(
                kind=ParseErrorKind.NOT_A_MAPPING,
                detail=f"frontmatter parsed to {type_name}, expected mapping",
            ),
        )

    return ParseResult(frontmatter=fm, body=body, error=None)


def _parse(content: str) -> ParseResult:
    if not content.startswith("---"):
        return ParseResult(frontmatter=None, body=content, error=None)

    lines = content.split("\n")
    if not _DELIMITER_LINE_RE.match(lines[0]):
        return ParseResult(
            frontmatter=None,
            body=content,
            error=ParseError(
                kind=ParseErrorKind.MALFORMED_DELIMITER,
                detail="opening --- must be alone on its line",
            ),
        )

    close_idx = next(
        (i for i in range(1, len(lines)) if _DELIMITER_LINE_RE.match(lines[i])),
        None,
    )
    if close_idx is None:
        return ParseResult(
            frontmatter=None,
            body=content,
            error=ParseError(
                kind=ParseErrorKind.MALFORMED_DELIMITER,
                detail="opening --- without closing ---",
            ),
        )

    raw = "\n".join(lines[1:close_idx])
    body = "\n".join(lines[close_idx + 1 :])
    return _load_frontmatter(raw, body)


def parse(content: str) -> tuple[dict[str, Any] | None, str]:
    """Common case. Never raises for expected error conditions.

    Returns (frontmatter, body). When frontmatter is absent or broken,
    frontmatter is None. body is always present.
    """
    result = _parse(content)
    return result.frontmatter, result.body


def parse_detailed(content: str) -> ParseResult:
    """Validator case. Full result with structured error details."""
    return _parse(content)
