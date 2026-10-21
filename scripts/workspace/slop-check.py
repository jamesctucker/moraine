#!/usr/bin/env python3
"""slop-check — deterministic code-quality measurement (flag-only, never fixes).

Implements the two SlopCodeBench trajectory metrics for garage repos
(SlopCodeBench, arXiv 2603.24755):

  Erosion   = share of complexity mass (CC * sqrt(NLOC) per callable) held by
              callables with CC > 10.  [paper eq. 2-3; CC cutoff per Radon]
  Verbosity = |ast-grep flagged lines UNION clone lines| / NLOC.  [paper eq. 4]

Plus three computed checks not expressible as ast-grep patterns (Python only):
single-use variable, if/elif ladder (>= 3 elifs), nesting depth >= 4.

Tool requirements (resolved on demand, nothing to pip-install):
  - lizard  via uvx (pinned 1.24.1)        — erosion, NLOC
  - ast-grep on PATH (sg)                  — rule-flagged lines
  - jscpd   via npx (pinned 5.4.2)         — clone lines

Usage:
  slop-check.py --repo work/rolodex            # snapshot a working tree
  slop-check.py --repo . --range main..HEAD    # base-vs-head delta (temp worktree)
  slop-check.py --all --json --write           # monthly sweep -> memory/eval/slop/
  slop-check.py --changed-only --fail-on-new   # pre-commit / PR gate

Thresholds (straight from the paper, SlopCodeBench arXiv 2603.24755):
  absolute  erosion  green<=0.34 warn<=0.68 red>0.68   (Table 2 human/agent means)
  absolute  verbosity green<=0.19 warn<=0.44 red>0.44
  delta     erosion  green<=0.0053 warn<=0.0264         (§3.3 human/agent velocity)
  delta     verbosity green<=0.0022 warn<=0.0144

Conventions:
  - Flag-only: exit 0 always, except --fail-on-new / --fail-on-new-cc (exit 1).
  - Missing/unmeasurable values are recorded as null, never imputed (paper §2.4).
  - Gate on delta, report absolute. Repos listed in slop-check.json's
    "grandfathered" (ported legacy) are delta-gated only — absolute bands
    never fail them.
  - Test files are excluded by default (--include-tests to override); the
    paper's repo panel did not exclude tests, so snapshot comparability with
    paper numbers is approximate. Pick one and freeze it.
"""

import argparse
import ast
import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from lib import WORKSPACE

LIZARD_VERSION = "1.24.1"
JSCPD_VERSION = "5.4.2"
RULES_CONFIG = WORKSPACE / "scripts" / "workspace" / "slop-rules" / "sgconfig.yml"
SLOP_DIR = WORKSPACE / "memory" / "eval" / "slop"

ABS_THRESH = {"erosion": (0.34, 0.68), "verbosity": (0.19, 0.44)}
DELTA_THRESH = {"erosion": (0.0053, 0.0264), "verbosity": (0.0022, 0.0144)}

SLOP_CONFIG = WORKSPACE / "slop-check.json"


def load_grandfathered() -> set[str]:
    """Repos exempt from absolute bands (ported legacy) — delta-gated only.

    Config lives in <workspace>/slop-check.json: {"grandfathered": ["repo-name"]}.
    Template default is empty; freeze baselines on first run, then grandfather
    only repos you deliberately imported messy.
    """
    if not SLOP_CONFIG.is_file():
        return set()
    try:
        data = json.loads(SLOP_CONFIG.read_text())
    except ValueError:
        print(f"warning: {SLOP_CONFIG} is not valid JSON; ignoring", file=sys.stderr)
        return set()
    return set(data.get("grandfathered", []))


GRANDFATHERED = load_grandfathered()

ALWAYS_EXCLUDE = [
    "**/node_modules/**", "**/.venv/**", "**/venv/**", "**/.git/**",
    "**/dist/**", "**/build/**", "**/.next/**", "**/coverage/**",
    "**/__pycache__/**", "**/vendor/**", "**/.tox/**", "**/site-packages/**",
]
TEST_EXCLUDE = [
    "**/tests/**", "**/test/**", "**/test_*.py", "**/*_test.py",
    "**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx",
    "**/cypress/**", "**/fixtures/**", "**/__tests__/**",
]

SCANNABLE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
                      ".mts", ".cts", ".rb", ".swift"}

EXCLUDE_DIRS = {
    "node_modules", ".venv", "venv", ".git", "dist", "build", ".next",
    "coverage", "__pycache__", "vendor", ".tox", "site-packages",
}
TEST_DIRS = {"tests", "test", "__tests__", "cypress", "fixtures"}
TEST_FILE_PATTERNS = ("test_*.py", "*_test.py", "*.test.ts", "*.test.tsx",
                      "*.spec.ts", "*.spec.tsx")


def iter_source_files(path: Path, include_tests: bool = False) -> list[Path]:
    """Scannable source files under path, honoring the standard exclusions."""
    from fnmatch import fnmatch
    candidates = [path] if path.is_file() else (p for p in path.rglob("*") if p.is_file())
    out = []
    for f in candidates:
        if f.suffix not in SCANNABLE_SUFFIXES:
            continue
        parts = set(f.parts)
        if parts & EXCLUDE_DIRS:
            continue
        if not include_tests and (parts & TEST_DIRS or
                                  any(fnmatch(f.name, p) for p in TEST_FILE_PATTERNS)):
            continue
        out.append(f)
    return sorted(out)


_COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")


def count_nloc(path: Path, include_tests: bool = False) -> int:
    """Non-blank, non-comment lines across scannable files — the verbosity
    denominator.

    Deliberately independent of lizard: flagged and clone lines can land in
    module-level code and in languages lizard doesn't parse, so the
    denominator must cover every line the numerator can touch. Comment-marker
    lines are stripped per the upstream SCB `loc` definition ("excludes
    comments and blanks", SCB docs/metrics-reference.md); Python docstring
    interiors still count — a known, documented imperfection.
    Consistency across snapshots matters more than perfection.
    """
    total = 0
    for f in iter_source_files(path, include_tests):
        try:
            for line in f.read_text(errors="replace").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith(_COMMENT_PREFIXES):
                    total += 1
        except OSError:
            continue
    return total


# ---------------------------------------------------------------- tool runners

def run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def lizard_callables(path: Path, excludes: list[str]) -> list[dict] | None:
    """Per-callable {file, start, end, ccn, nloc} from lizard CSV."""
    cmd = ["uvx", "--from", f"lizard=={LIZARD_VERSION}", "lizard", "--csv"]
    for pat in excludes:
        cmd += ["-x", pat]
    cmd.append(str(path))
    try:
        res = run(cmd)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if res.returncode != 0 and not res.stdout.strip():
        return None
    rows: list[dict] = []
    reader = csv.reader(res.stdout.splitlines())
    for row in reader:
        if not row:
            continue
        # lizard --csv emits no header; positional layout is:
        # nloc,ccn,token,param,length,location,file,function,long_name,start,end
        if row[0].strip().upper() == "NLOC":
            continue  # tolerate a header if a future lizard adds one
        try:
            rows.append({
                "file": row[6],
                "start": int(row[9]), "end": int(row[10]),
                "ccn": int(row[1]), "nloc": int(row[0]),
            })
        except (IndexError, ValueError):
            continue
    return rows


def erosion_from(callables: list[dict]) -> tuple[float | None, int, int]:
    """(erosion, nloc_total, max_cc). Erosion is None when no mass."""
    total_mass = 0.0
    high_mass = 0.0
    nloc_total = 0
    max_cc = 0
    for c in callables:
        mass = c["ccn"] * math.sqrt(max(c["nloc"], 1))
        total_mass += mass
        nloc_total += c["nloc"]
        max_cc = max(max_cc, c["ccn"])
        if c["ccn"] > 10:
            high_mass += mass
    if total_mass == 0:
        return None, nloc_total, max_cc
    return high_mass / total_mass, nloc_total, max_cc


def astgrep_lines(path: Path) -> tuple[set[tuple[str, int]], dict[str, int]] | None:
    """(file, 1-based line) set flagged by the slop-rules pack + hits by rule id."""
    cmd = ["ast-grep", "scan", "--config", str(RULES_CONFIG), "--json", str(path)]
    try:
        res = run(cmd)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    out = res.stdout.strip()
    if not out:
        return set(), {}
    try:
        matches = json.loads(out)
    except json.JSONDecodeError:
        return None
    lines: set[tuple[str, int]] = set()
    hits: dict[str, int] = {}
    for m in matches:
        f = m.get("file", "")
        if Path(f).suffix not in SCANNABLE_SUFFIXES:
            continue
        rng = m.get("range", {})
        start = rng.get("start", {}).get("line", 0) + 1  # ast-grep is 0-based
        end = rng.get("end", {}).get("line", start - 1) + 1
        rid = m.get("ruleId", "unknown")
        for ln in range(start, end + 1):
            lines.add((f, ln))
            hits[rid] = hits.get(rid, 0) + 1
    return lines, hits


def jscpd_lines(path: Path, excludes: list[str]) -> set[tuple[str, int]] | None:
    """Clone lines (firstFile side of each duplicate) as (file, line) tuples."""
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            "npx", "-y", f"jscpd@{JSCPD_VERSION}", str(path),
            "--reporters", "json", "--output", tmp,
            "--ignore", ",".join(excludes), "--silent",
        ]
        try:
            res = run(cmd, timeout=600)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        report = Path(tmp) / "jscpd-report.json"
        if not report.is_file():
            return None
        try:
            data = json.loads(report.read_text())
        except json.JSONDecodeError:
            return None
        lines: set[tuple[str, int]] = set()
        for dup in data.get("duplicates", []):
            first = dup.get("firstFile", {})
            name, start, end = first.get("name"), first.get("start"), first.get("end")
            if not name or start is None or end is None:
                continue
            if Path(name).suffix not in SCANNABLE_SUFFIXES:
                continue
            for ln in range(start, end + 1):
                lines.add((name, ln))
        return lines


# ------------------------------------------------------------ computed checks

def computed_checks(path: Path) -> tuple[set[tuple[str, int]], dict[str, int]]:
    """Python-only checks not expressible as ast-grep patterns."""
    lines: set[tuple[str, int]] = set()
    hits: dict[str, int] = {}

    def add(rid: str, f: str, ln: int) -> None:
        lines.add((f, ln))
        hits[rid] = hits.get(rid, 0) + 1

    files = [path] if path.is_file() else sorted(path.rglob("*.py"))
    for f in files:
        if any(part in {"tests", "test", "__tests__", "fixtures"} for part in f.parts):
            continue
        try:
            tree = ast.parse(f.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = str(f)

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):  # noqa: N802
                self._func(node)
                self.generic_visit(node)

            visit_AsyncFunctionDef = visit_FunctionDef

            def _func(self, node):
                # Single-use variable: `tmp = <expr>` immediately followed by
                # `return tmp`, with no other loads — the Listing 5 pattern of
                # naming an intermediate only to return it. Narrow on purpose:
                # broader single-use definitions flag ordinary code and swamp
                # the metric's absolute calibration (paper band 0.19–0.44).
                body = node.body
                for i, stmt in enumerate(body[:-1]):
                    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                        continue
                    target = stmt.targets[0]
                    if not isinstance(target, ast.Name):
                        continue
                    nxt = body[i + 1]
                    if not (isinstance(nxt, ast.Return) and isinstance(nxt.value, ast.Name)
                            and nxt.value.id == target.id):
                        continue
                    rest_loads = [
                        n for s in body[i + 2:] for n in ast.walk(s)
                        if isinstance(n, ast.Name) and n.id == target.id
                        and isinstance(n.ctx, ast.Load)
                    ]
                    if not rest_loads:
                        add("py-single-use-var", rel, stmt.lineno)

        Visitor().visit(tree)

        # if/elif ladder (>= 3 elifs) and nesting depth >= 4, via parent walk.
        # Deep nesting flags only the statement that CROSSES the threshold
        # (depth == 3); descendants of an already-deep statement don't re-fire.
        # An elif continuation (an If as the sole orelse of an If) stays at the
        # parent's depth — elif chains are flat, not nested.
        def walk(n: ast.AST, depth: int) -> None:
            for child in ast.iter_child_nodes(n):
                is_elif = (isinstance(n, ast.If) and isinstance(child, ast.If)
                           and len(n.orelse) == 1 and n.orelse[0] is child)
                if isinstance(child, ast.If) and not is_elif:
                    elifs = 0
                    cur = child
                    while cur.orelse and len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                        elifs += 1
                        cur = cur.orelse[0]
                    if elifs >= 3:
                        add("py-elif-ladder", rel, child.lineno)
                nested = isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)) and not is_elif
                if nested and depth == 3:
                    add("py-deep-nesting", rel, child.lineno)
                walk(child, depth + 1 if nested else depth)

        walk(tree, 0)
    return lines, hits


# ------------------------------------------------------------------ measuring

def band(value: float | None, green: float, warn: float) -> str | None:
    if value is None:
        return None
    return "green" if value <= green else "warn" if value <= warn else "red"


def measure(repo_path: Path, include_tests: bool = False) -> dict:
    excludes = ALWAYS_EXCLUDE + ([] if include_tests else TEST_EXCLUDE)
    callables = lizard_callables(repo_path, excludes)
    if callables is None:
        return {"error": "lizard failed or timed out", "erosion": None,
                "verbosity": None, "nloc": None}
    erosion, func_nloc, max_cc = erosion_from(callables)
    cc_over_10 = sum(1 for c in callables if c["ccn"] > 10)
    nloc = count_nloc(repo_path, include_tests)

    rule_result = astgrep_lines(repo_path)
    rule_lines, rule_hits = rule_result if rule_result else (set(), None)
    comp_lines, comp_hits = computed_checks(repo_path)
    if rule_hits is not None:
        for rid, n in comp_hits.items():
            rule_hits[rid] = rule_hits.get(rid, 0) + n
    flagged = rule_lines | comp_lines

    clone_lines = jscpd_lines(repo_path, excludes)
    if rule_hits is None or clone_lines is None or not nloc:
        verbosity = None
    else:
        union = flagged | clone_lines
        verbosity = min(len(union) / nloc, 1.0) if nloc else None

    return {
        "callables": len(callables),
        "erosion": round(erosion, 4) if erosion is not None else None,
        "verbosity": round(verbosity, 4) if verbosity is not None else None,
        "nloc": nloc,
        "func_nloc": func_nloc,
        "max_cc": max_cc,
        "cc_over_10": cc_over_10,
        "rule_hits_by_id": rule_hits,
        "rule_lines": len(flagged),
        "clone_lines": len(clone_lines) if clone_lines is not None else None,
    }


def git_commit(repo_path: Path) -> str | None:
    res = run(["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"], timeout=15)
    return res.stdout.strip() if res.returncode == 0 else None


def tool_versions() -> dict:
    def ver(cmd: list[str]) -> str | None:
        try:
            res = run(cmd, timeout=60)
            return res.stdout.strip().splitlines()[0] if res.stdout.strip() else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    return {
        "lizard": LIZARD_VERSION,
        "ast_grep": (ver(["ast-grep", "--version"]) or "unknown").split()[-1],
        "jscpd": JSCPD_VERSION,
    }


def snapshot(repo_rel: str, repo_path: Path, include_tests: bool = False) -> dict:
    m = measure(repo_path, include_tests)
    exclude_blob = json.dumps(ALWAYS_EXCLUDE + TEST_EXCLUDE, sort_keys=True).encode()
    snap = {
        "repo": repo_rel,
        "commit": git_commit(repo_path),
        "date": date.today().isoformat(),
        "tool_versions": tool_versions(),
        "exclude_globs_hash": hashlib.sha1(exclude_blob).hexdigest()[:12],
        "tests_excluded": not include_tests,
        **m,
        "grandfathered": repo_rel.split("/")[-1] in GRANDFATHERED,
        "bands": {
            "erosion": band(m.get("erosion"), *ABS_THRESH["erosion"]),
            "verbosity": band(m.get("verbosity"), *ABS_THRESH["verbosity"]),
        },
        "prev": None,
        "delta": {"erosion": None, "verbosity": None},
    }
    return snap


# ------------------------------------------------------------------ reporting

def fmt(v: float | None) -> str:
    return "  null" if v is None else f"{v:.3f}"


def print_snapshot(snap: dict) -> None:
    g = " [grandfathered]" if snap.get("grandfathered") else ""
    print(f"\n== {snap['repo']} @ {snap.get('commit') or '?'}{g}")
    if snap.get("error"):
        print(f"   ERROR: {snap['error']}")
        return
    eb, vb = snap["bands"]["erosion"], snap["bands"]["verbosity"]
    print(f"   erosion   {fmt(snap['erosion'])}  {eb or '?':5s}   "
          f"(callables {snap['callables']}, CC>10: {snap['cc_over_10']}, max CC {snap['max_cc']})")
    print(f"   verbosity {fmt(snap['verbosity'])}  {vb or '?':5s}   "
          f"(rule lines {snap.get('rule_lines')}, clone lines {snap.get('clone_lines')}, NLOC {snap['nloc']})")
    d = snap["delta"]
    if d["erosion"] is not None or d["verbosity"] is not None:
        de, dv = d["erosion"], d["verbosity"]
        deb = band(de, *DELTA_THRESH["erosion"]) if de is not None else None
        dvb = band(dv, *DELTA_THRESH["verbosity"]) if dv is not None else None
        print(f"   delta     erosion {de:+.4f} ({deb})  verbosity {dv:+.4f} ({dvb})  vs {snap['prev']}")
    hits = snap.get("rule_hits_by_id") or {}
    if hits:
        top = sorted(hits.items(), key=lambda kv: -kv[1])[:5]
        print("   top rules: " + ", ".join(f"{rid} x{n}" for rid, n in top))


def snapshot_path(repo_rel: str, month: str) -> Path:
    slug = repo_rel.replace("/", "__")
    return SLOP_DIR / "snapshots" / month / f"{slug}.json"


def link_prev(snap: dict, month: str) -> None:
    """Find the most recent earlier snapshot for this repo and compute deltas."""
    slug = snap["repo"].replace("/", "__")
    candidates = sorted(
        p for p in SLOP_DIR.glob(f"snapshots/*/{slug}.json")
        if p.parent.name < month
    )
    if not candidates:
        return
    prev_path = candidates[-1]
    try:
        prev = json.loads(prev_path.read_text())
    except json.JSONDecodeError:
        return
    snap["prev"] = str(prev_path.relative_to(WORKSPACE))
    for key in ("erosion", "verbosity"):
        if snap.get(key) is not None and prev.get(key) is not None:
            snap["delta"][key] = round(snap[key] - prev[key], 4)


# --------------------------------------------------------------------- modes

def discover_repos() -> list[tuple[str, Path]]:
    repos: list[tuple[str, Path]] = []
    work = WORKSPACE / "work"
    if work.is_dir():
        for d in sorted(work.iterdir()):
            if d.is_dir() and (d / ".git").exists():
                repos.append((f"work/{d.name}", d))
    repos.append(("scripts/workspace", WORKSPACE / "scripts" / "workspace"))
    return repos


def mode_all(args) -> int:
    month = date.today().strftime("%Y-%m")
    snaps = []
    for rel, path in discover_repos():
        print(f"measuring {rel} ...", file=sys.stderr)
        snap = snapshot(rel, path, args.include_tests)
        if args.write:
            link_prev(snap, month)
        snaps.append(snap)
        print_snapshot(snap)
    if args.write:
        out_dir = SLOP_DIR / "snapshots" / month
        out_dir.mkdir(parents=True, exist_ok=True)
        for snap in snaps:
            p = snapshot_path(snap["repo"], month)
            p.write_text(json.dumps(snap, indent=2) + "\n")
        print(f"\nwrote {len(snaps)} snapshots -> {out_dir.relative_to(WORKSPACE)}")
    if args.json:
        print(json.dumps(snaps, indent=2))
    return 0


def mode_repo(args) -> int:
    repo_path = Path(args.repo).resolve()
    rel = args.repo
    if args.range:
        return mode_range(args, repo_path, rel)
    snap = snapshot(rel, repo_path, args.include_tests)
    if args.json:
        print(json.dumps(snap, indent=2))
    else:
        print_snapshot(snap)
    if args.write:
        month = date.today().strftime("%Y-%m")
        link_prev(snap, month)
        p = snapshot_path(rel, month)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(snap, indent=2) + "\n")
        print(f"wrote {p.relative_to(WORKSPACE)}")
    return 0


def mode_range(args, repo_path: Path, rel: str) -> int:
    base, _, head_ref = args.range.partition("..")
    # The worktree holds the whole git root; measure the same subpath inside it.
    root_res = run(["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"], timeout=15)
    if root_res.returncode != 0:
        print(f"not inside a git repo: {repo_path}", file=sys.stderr)
        return 1
    git_root = Path(root_res.stdout.strip()).resolve()
    sub = repo_path.resolve().relative_to(git_root)

    def measure_ref(ref: str):
        """Measure a git ref in a throwaway worktree (never touches the user's tree)."""
        with tempfile.TemporaryDirectory() as tmp:
            res = run(["git", "-C", str(git_root), "worktree", "add", "--detach", tmp, ref])
            if res.returncode != 0:
                print(f"git worktree add failed: {res.stderr.strip()}", file=sys.stderr)
                return None
            try:
                return measure(Path(tmp) / sub, args.include_tests)
            finally:
                run(["git", "-C", str(git_root), "worktree", "remove", "--force", tmp])

    print(f"measuring base {base} ...", file=sys.stderr)
    base_snap = measure_ref(base)
    if base_snap is None:
        return 1
    if head_ref in ("", "HEAD"):
        # Live working tree: captures uncommitted milestone state (step 4b flow).
        print("measuring head (working tree) ...", file=sys.stderr)
        head_snap = measure(repo_path, args.include_tests)
    else:
        print(f"measuring head {head_ref} ...", file=sys.stderr)
        head_snap = measure_ref(head_ref)
        if head_snap is None:
            return 1
    result = {"repo": rel, "range": args.range, "base": base_snap, "head": head_snap, "delta": {}}
    for key in ("erosion", "verbosity"):
        b, h = base_snap.get(key), head_snap.get(key)
        result["delta"][key] = round(h - b, 4) if b is not None and h is not None else None
    b_cc, h_cc = base_snap.get("cc_over_10"), head_snap.get("cc_over_10")
    new_cc = (h_cc - b_cc) if b_cc is not None and h_cc is not None else 0
    result["delta"]["new_cc_over_10"] = new_cc
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n== {rel} range {args.range}")
        for key in ("erosion", "verbosity"):
            d = result["delta"][key]
            bnd = band(d, *DELTA_THRESH[key]) if d is not None else None
            print(f"   {key:9s} base {fmt(base_snap.get(key))} -> head {fmt(head_snap.get(key))}  "
                  f"delta {d:+.4f} ({bnd})" if d is not None else f"   {key:9s} unavailable")
        print(f"   new CC>10 callables: {new_cc}")
    if args.fail_on_new_cc and new_cc > 0:
        print(f"FAIL: diff introduces {new_cc} new callable(s) with CC > 10 "
              f"(extract the seam first — implement-milestone step 4b)", file=sys.stderr)
        return 1
    return 0


def mode_changed(args) -> int:
    res = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], timeout=15)
    names = res.stdout.split() if res.returncode == 0 else []
    if not names:
        res = run(["git", "diff", "--name-only", "--diff-filter=ACM", "HEAD"], timeout=15)
        names = res.stdout.split() if res.returncode == 0 else []
    files = [WORKSPACE / f for f in names
             if Path(f).suffix in SCANNABLE_SUFFIXES and (WORKSPACE / f).is_file()]
    if not files:
        print("no scannable changed files")
        return 0
    new_hits: list[str] = []
    for f in files:
        rule_result = astgrep_lines(f)
        if rule_result:
            lines, hits = rule_result
            for _f, ln in sorted(lines):
                new_hits.append(f"{f.relative_to(WORKSPACE)}:{ln}")
        _, comp_hits = computed_checks(f)
        if comp_hits:
            new_hits.append(f"{f.relative_to(WORKSPACE)}: computed {comp_hits}")
        callables = lizard_callables(f, [])
        for c in callables or []:
            if c["ccn"] > 20:
                new_hits.append(f"{f.relative_to(WORKSPACE)}:{c['start']} CC {c['ccn']} > 20")
    if new_hits:
        print("slop-check findings in changed files:")
        for h in new_hits:
            print(f"  {h}")
        if args.fail_on_new:
            return 1
    else:
        print(f"clean: {len(files)} changed files, no findings")
    return 0
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", help="Repo path (relative to workspace or absolute)")
    p.add_argument("--range", metavar="BASE..HEAD", help="Measure delta across a range (temp worktree)")
    p.add_argument("--all", action="store_true", help="Measure all work/ repos + scripts/workspace")
    p.add_argument("--json", action="store_true", help="Emit JSON")
    p.add_argument("--write", action="store_true", help="Write snapshots to memory/eval/slop/")
    p.add_argument("--changed-only", action="store_true", help="Scan staged/changed files only")
    p.add_argument("--fail-on-new", action="store_true", help="Exit 1 on findings in changed files")
    p.add_argument("--fail-on-new-cc", action="store_true",
                   help="With --range: exit 1 if the diff introduces new CC>10 callables")
    p.add_argument("--include-tests", action="store_true", help="Include test files (excluded by default)")
    args = p.parse_args()

    if args.all:
        return mode_all(args)
    if args.changed_only:
        return mode_changed(args)
    if args.repo:
        return mode_repo(args)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
