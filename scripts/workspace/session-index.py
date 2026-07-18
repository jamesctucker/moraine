#!/usr/bin/env python3
"""Session search indexer — builds FTS5 index over memory/sessions/ and memory/staging/."""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

from lib import WORKSPACE, extract_wikilinks
SESSIONS_DIR = WORKSPACE / "memory" / "sessions"
STAGING_DIR = WORKSPACE / "memory" / "staging"
DB_DIR = WORKSPACE / "memory" / ".index"
DB_PATH = DB_DIR / "sessions.db"

SECTION_ALIASES = {
    "accomplished": "accomplishments",
    "in progress": "in_progress",
    "artifacts": "artifacts",
    "decisions": "decisions",
    "session notes": "notes",
    "notes": "notes",
}

WORK_REPO_RE = re.compile(r"work/([^/]+)/")


def parse_date_title(content: str, path: Path) -> tuple[str, str] | None:
    first_line = content.split("\n", 1)[0].strip()
    m = re.match(r"#\s+(\d{4}-\d{2}-\d{2}):\s+(.+)", first_line)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"#\s+Staging\s+[—–-]\s+(\d{4}-\d{2}-\d{2})", first_line)
    if m:
        d = m.group(1)
        return d, f"Staging {d}"
    return None


def extract_projects(text: str) -> list[str]:
    projects: set[str] = set()
    for wikilink in extract_wikilinks(text):
        link = wikilink.strip()
        if link.endswith(".md"):
            stem = Path(link).stem
            projects.add(stem)
    for m in WORK_REPO_RE.finditer(text):
        projects.add(m.group(1).replace("_", "-"))
    return sorted(projects)


def parse_sections(content: str) -> list[tuple[str, str]]:
    lines = content.split("\n")
    sections: list[tuple[str, str]] = []
    current_section = ""
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if current_lines:
                sections.append((current_section, "\n".join(current_lines)))
            heading = m.group(1).strip().lower()
            current_section = SECTION_ALIASES.get(heading, "")
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_section, "\n".join(current_lines)))
    return sections


def rebuild_index() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    conn.execute("DROP TABLE IF EXISTS sessions")
    conn.execute(
        """CREATE VIRTUAL TABLE sessions USING fts5(
            date, title, content, section, project_links,
            tokenize='porter unicode61'
        )"""
    )

    md_files = sorted(SESSIONS_DIR.glob("*.md")) + sorted(STAGING_DIR.glob("*.md"))
    rows = []

    for path in md_files:
        content = path.read_text(encoding="utf-8")
        parsed = parse_date_title(content, path)
        if not parsed:
            print(f"  Skipping {path.name}: could not parse date/title", file=sys.stderr)
            continue
        date_str, title = parsed
        full_text = content
        projects = extract_projects(content)
        project_str = " ".join(projects)

        sections = parse_sections(content)
        if not sections:
            rows.append((date_str, title, full_text.strip(), "", project_str))
        else:
            for section_name, section_content in sections:
                text = section_content.strip()
                if text:
                    rows.append((date_str, title, text, section_name, project_str))

    conn.executemany(
        "INSERT INTO sessions (date, title, content, section, project_links) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Indexed {len(md_files)} files → {len(rows)} rows in {DB_PATH}")


def normalize_fts_query(query: str) -> str:
    """Wrap hyphenated terms in quotes so FTS5 doesn't interpret '-' as NOT."""
    return " ".join(
        f'"{t}"' if "-" in t and not t.startswith('"') else t
        for t in query.split()
    )


def search_index(query: str, limit: int = 10, dates: str | None = None,
                 section: str | None = None, project: str | None = None) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    fts_query = normalize_fts_query(query)
    conditions: list[str] = ["sessions MATCH ?"]
    params: list[str] = [fts_query]

    if section:
        conditions.append("section = ?")
        params.append(section)
    if project:
            alt = project.replace("-", "_") if "-" in project else project.replace("_", "-")
            conditions.append("(project_links LIKE ? OR project_links LIKE ?)")
            params.extend([f"%{project}%", f"%{alt}%"])
    if dates:
        parts = dates.split("..", 1)
        conditions.append("date >= ? AND date <= ?")
        params.extend([parts[0], parts[1] if len(parts) > 1 else parts[0]])

    sql = f"""SELECT date, title, snippet(sessions, 2, '<b>', '</b>', '...', 48) AS snippet,
                     section, project_links
              FROM sessions
              WHERE {' AND '.join(conditions)}
              ORDER BY rank LIMIT ?"""
    params.append(limit)

    results = []
    for row in conn.execute(sql, params):
        results.append({
            "date": row["date"],
            "title": row["title"],
            "snippet": row["snippet"],
            "section": row["section"],
            "project_links": row["project_links"] or "",
        })
    conn.close()
    return results


def cmd_index() -> None:
    rebuild_index()


def cmd_search(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("No index found. Run 'session-index.py index' first.", file=sys.stderr)
        sys.exit(1)

    results = search_index(
        query=args.query,
        limit=args.limit,
        dates=args.dates,
        section=args.section,
        project=args.project,
    )

    if not results:
        print("No matches found.")
        return

    for r in results:
        sec_tag = f" [{r['section']}]" if r["section"] else ""
        proj_tag = f" projects: {r['project_links']}" if r["project_links"] else ""
        print(f"\n## {r['date']}: {r['title']}{sec_tag}{proj_tag}")
        print(f"   {r['snippet']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Session search indexer")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="Rebuild the search index")

    search_parser = sub.add_parser("search", help="Search sessions")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    search_parser.add_argument("--dates", help="Date range: YYYY-MM-DD..YYYY-MM-DD")
    search_parser.add_argument("--section", choices=sorted(SECTION_ALIASES.values()),
                               help="Filter by section (e.g. decisions, accomplishments)")
    search_parser.add_argument("--project", help="Filter by project link (e.g. my-api)")

    parsed = parser.parse_args()

    if parsed.command == "index":
        cmd_index()
    elif parsed.command == "search":
        cmd_search(parsed)


if __name__ == "__main__":
    main()
