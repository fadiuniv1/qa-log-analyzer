#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

DEFAULT_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


_date_time_re = re.compile(
    r"\b(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)\b"
)
_date_only_re = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2})\b")


def _extract_timestamp(line: str) -> Optional[datetime]:
    match = _date_time_re.search(line)
    if match:
        date_part, time_part = match.groups()
        try:
            return datetime.fromisoformat(f"{date_part}T{time_part}")
        except ValueError:
            return None
    match = _date_only_re.search(line)
    if match:
        date_part = match.group(1).replace("/", "-")
        try:
            return datetime.fromisoformat(date_part)
        except ValueError:
            return None
    return None


def _parse_dt_arg(value: str) -> datetime:
    normalized = value.strip()
    if " " in normalized and "T" not in normalized:
        normalized = normalized.replace(" ", "T", 1)
    if "/" in normalized and "T" not in normalized:
        normalized = normalized.replace("/", "-")
    return datetime.fromisoformat(normalized)


def iter_lines(
    path: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_untimestamped: bool = False,
):
    if path == "-":
        source = sys.stdin
    else:
        source = open(path, "r", encoding="utf-8", errors="ignore")
    try:
        for raw in source:
            line = raw.rstrip("\n")
            if since is None and until is None:
                yield line
                continue
            ts = _extract_timestamp(line)
            if ts is None:
                if include_untimestamped:
                    yield line
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
            yield line
    finally:
        if source is not sys.stdin:
            source.close()


def _compile_keyword(pattern: str, use_regex: bool, ignore_case: bool, whole_word: bool) -> re.Pattern:
    flags = re.IGNORECASE if ignore_case else 0
    if use_regex:
        if whole_word:
            pattern = rf"\b(?:{pattern})\b"
        return re.compile(pattern, flags)
    escaped = re.escape(pattern)
    if whole_word:
        escaped = rf"\b{escaped}\b"
    return re.compile(escaped, flags)


def count_pattern(
    path: str,
    pattern: str,
    use_regex: bool = False,
    ignore_case: bool = False,
    whole_word: bool = False,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_untimestamped: bool = False,
) -> int:
    rx = _compile_keyword(pattern, use_regex, ignore_case, whole_word)
    return sum(
        1
        for line in iter_lines(
            path, since=since, until=until, include_untimestamped=include_untimestamped
        )
        if rx.search(line)
    )


def _compile_levels(levels: Iterable[str]) -> List[Tuple[str, re.Pattern]]:
    compiled = []
    for lvl in levels:
        if not lvl:
            continue
        compiled.append((lvl, re.compile(rf"\b{re.escape(lvl)}\b")))
    return compiled


def severity_summary(
    path: str,
    levels=DEFAULT_LEVELS,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_untimestamped: bool = False,
) -> dict:
    counts = Counter()
    compiled_levels = _compile_levels(levels)
    for line in iter_lines(path, since=since, until=until, include_untimestamped=include_untimestamped):
        for lvl, rx in compiled_levels:
            # conservative rule: match whole word level tokens
            if rx.search(line):
                counts[lvl] += 1
                break
    # return a stable dict with all levels (even if 0)
    return {lvl: int(counts.get(lvl, 0)) for lvl in levels}


# Normalization regexes (conservative)
_ts_re = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b|\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"
)
_iso_ts_re = re.compile(r"\b\d{4}/\d{2}/\d{2}\b")
_hex_re = re.compile(r"\b0x[0-9a-fA-F]+\b")
_uuid_re = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_num_re = re.compile(r"\b\d+\b")
_path_re = re.compile(r"(/[^\s]+)+")  # simple path collapse


def _normalize_line(line: str) -> str:
    # Keep it conservative and deterministic:
    # 1) Use only the first physical line (avoid stack traces)
    line = line.split("\n", 1)[0]
    # 2) Remove common timestamps
    line = _ts_re.sub("", line)
    line = _iso_ts_re.sub("", line)
    # 3) Replace hex, uuids, numeric ids, and file paths
    line = _hex_re.sub("<HEX>", line)
    line = _uuid_re.sub("<UUID>", line)
    line = _path_re.sub("<PATH>", line)
    line = _num_re.sub("<NUM>", line)
    # 4) Collapse whitespace
    return " ".join(line.split()).strip()


def group_messages(
    path: str,
    top_n: int = 10,
    min_count: int = 1,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_untimestamped: bool = False,
) -> List[Tuple[int, str, int, int]]:
    """
    Returns a list of tuples: (count, sample_line, first_seen_line_no, last_seen_line_no)
    Ordered by count descending, limited to top_n.
    """
    counts = Counter()
    samples = {}
    first_seen = {}
    last_seen = {}
    for i, raw in enumerate(
        iter_lines(path, since=since, until=until, include_untimestamped=include_untimestamped), start=1
    ):
        key = _normalize_line(raw)
        if not key:
            continue
        counts[key] += 1
        samples.setdefault(key, raw)
        first_seen.setdefault(key, i)
        last_seen[key] = i
    items = [(k, c) for k, c in counts.items() if c >= min_count]
    items.sort(key=lambda item: item[1], reverse=True)
    top = items[:top_n]
    return [(c, samples[k], first_seen[k], last_seen[k]) for k, c in top]


def file_stats(
    path: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_untimestamped: bool = False,
) -> dict:
    total = 0
    empty = 0
    unique_lines = set()
    for line in iter_lines(path, since=since, until=until, include_untimestamped=include_untimestamped):
        total += 1
        if not line.strip():
            empty += 1
        unique_lines.add(line)
    return {
        "total_lines": total,
        "empty_lines": empty,
        "non_empty_lines": total - empty,
        "unique_lines": len(unique_lines),
    }


def _parse_levels(levels_raw: str) -> Tuple[str, ...]:
    parts = [p.strip() for p in levels_raw.split(",")]
    levels = tuple(p for p in parts if p)
    if not levels:
        raise ValueError("levels cannot be empty")
    return levels


def _parse_exit_codes(raw: str) -> dict:
    mapping = {}
    for entry in raw.split(","):
        if not entry.strip():
            continue
        if "=" not in entry:
            raise ValueError("exit codes must be in LEVEL=CODE format")
        level, code = entry.split("=", 1)
        level = level.strip()
        if not level:
            raise ValueError("exit code level cannot be empty")
        try:
            code_value = int(code.strip())
        except ValueError as exc:
            raise ValueError("exit code must be an integer") from exc
        if code_value < 0:
            raise ValueError("exit code must be non-negative")
        mapping[level] = code_value
    if not mapping:
        raise ValueError("exit codes cannot be empty")
    return mapping


def _schema_for(mode: str) -> dict:
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    if mode == "keyword":
        return {
            **base,
            "type": "object",
            "additionalProperties": False,
            "properties": {"keyword": {"type": "string"}, "count": {"type": "integer"}},
            "required": ["keyword", "count"],
        }
    if mode == "summary":
        return {
            **base,
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }
    if mode == "group":
        return {
            **base,
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "count": {"type": "integer"},
                    "sample": {"type": "string"},
                    "first_line": {"type": "integer"},
                    "last_line": {"type": "integer"},
                },
                "required": ["count", "sample", "first_line", "last_line"],
            },
        }
    if mode == "stats":
        return {
            **base,
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "total_lines": {"type": "integer"},
                "empty_lines": {"type": "integer"},
                "non_empty_lines": {"type": "integer"},
                "unique_lines": {"type": "integer"},
            },
            "required": ["total_lines", "empty_lines", "non_empty_lines", "unique_lines"],
        }
    raise ValueError(f"Unknown mode: {mode}")


def _format_table(headers: List[str], rows: List[List[object]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * widths[i] for i in range(len(headers)))
    body_lines = [
        " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) for row in rows
    ]
    return "\n".join([header_line, sep_line] + body_lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="log-analyzer",
        description="Analyze a log file: count keyword occurrences, produce a severity summary, or group similar messages.",
        epilog="Examples: python analyzer.py sample.log --keyword ERROR | python analyzer.py sample.log --summary --json | cat app.log | python analyzer.py - --group --top 5",
    )
    p.add_argument("logfile", help="Path to the log file to analyze. Use '-' to read from STDIN.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "-k",
        "--keyword",
        default=None,
        help="Keyword to search for (default: ERROR when used without flags)",
    )
    mode.add_argument("-s", "--summary", action="store_true", help="Show severity summary (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
    mode.add_argument("--group", action="store_true", help="Group similar messages and show top N")
    mode.add_argument("--stats", action="store_true", help="Show basic file stats (total, empty, unique)")
    p.add_argument("--top", type=int, default=10, help="Top N groups to show (used with --group)")
    p.add_argument("--min-count", type=int, default=1, help="Minimum group count to include (used with --group)")
    p.add_argument("--regex", action="store_true", help="Treat the keyword as a regular expression")
    p.add_argument("--whole-word", action="store_true", help="Match whole words only (keyword or regex)")
    p.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive keyword/regex matching")
    p.add_argument("--levels", default=None, help="Comma-separated summary levels (used with --summary)")
    p.add_argument("--since", default=None, help="Only include lines at or after this timestamp (ISO 8601)")
    p.add_argument("--until", default=None, help="Only include lines at or before this timestamp (ISO 8601)")
    p.add_argument(
        "--include-untimestamped",
        action="store_true",
        help="Include lines without timestamps when using --since/--until",
    )
    p.add_argument(
        "--exit-codes",
        default=None,
        help="Comma-separated summary exit codes, e.g. ERROR=2,CRITICAL=3 (used with --summary)",
    )
    p.add_argument("--schema", action="store_true", help="Output JSON schema for the selected mode")
    p.add_argument(
        "--format",
        choices=("text", "json", "table"),
        default="text",
        help="Output format preset (text, json, table). Overrides --json.",
    )
    p.add_argument("--json", action="store_true", help="Output as JSON (useful for automation/CI)")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.format != "text" and args.json:
        print("Cannot combine --format with --json", file=sys.stderr)
        return 2
    format_mode = "json" if args.json else args.format
    since = None
    until = None
    if args.since:
        try:
            since = _parse_dt_arg(args.since)
        except ValueError as exc:
            print(f"Invalid --since value: {exc}", file=sys.stderr)
            return 2
    if args.until:
        try:
            until = _parse_dt_arg(args.until)
        except ValueError as exc:
            print(f"Invalid --until value: {exc}", file=sys.stderr)
            return 2
    if since and until and since > until:
        print("Invalid time range: --since must be <= --until", file=sys.stderr)
        return 2

    # Grouping mode
    if args.group:
        if args.schema:
            print(json.dumps(_schema_for("group"), indent=2))
            return 0
        groups = group_messages(
            args.logfile,
            top_n=args.top,
            min_count=args.min_count,
            since=since,
            until=until,
            include_untimestamped=args.include_untimestamped,
        )
        if format_mode == "json":
            out = [
                {"count": c, "sample": s, "first_line": f, "last_line": l} for c, s, f, l in groups
            ]
            print(json.dumps(out, indent=2))
        elif format_mode == "table":
            rows = [[c, f, l, s] for c, s, f, l in groups]
            print(_format_table(["count", "first_line", "last_line", "sample"], rows))
        else:
            for c, s, f, l in groups:
                print(f"{c}x | lines {f}-{l} | {s}")
        return 0

    # Severity summary mode
    if args.summary:
        if args.schema:
            print(json.dumps(_schema_for("summary"), indent=2))
            return 0
        levels = DEFAULT_LEVELS
        if args.levels is not None:
            try:
                levels = _parse_levels(args.levels)
            except ValueError as exc:
                print(f"Invalid levels: {exc}", file=sys.stderr)
                return 2
        result = severity_summary(
            args.logfile,
            levels=levels,
            since=since,
            until=until,
            include_untimestamped=args.include_untimestamped,
        )
        if format_mode == "json":
            print(json.dumps(result, indent=2))
        elif format_mode == "table":
            rows = [[k, v] for k, v in result.items()]
            print(_format_table(["level", "count"], rows))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        # exit code: configurable by level, default ERROR/CRITICAL -> 1
        if args.exit_codes:
            try:
                exit_codes = _parse_exit_codes(args.exit_codes)
            except ValueError as exc:
                print(f"Invalid --exit-codes value: {exc}", file=sys.stderr)
                return 2
            matched = [code for level, code in exit_codes.items() if result.get(level, 0) > 0]
            return max(matched) if matched else 0
        return 0 if (result.get("ERROR", 0) == 0 and result.get("CRITICAL", 0) == 0) else 1

    # Stats mode
    if args.stats:
        if args.schema:
            print(json.dumps(_schema_for("stats"), indent=2))
            return 0
        stats = file_stats(
            args.logfile,
            since=since,
            until=until,
            include_untimestamped=args.include_untimestamped,
        )
        if format_mode == "json":
            print(json.dumps(stats, indent=2))
        elif format_mode == "table":
            rows = [[k, v] for k, v in stats.items()]
            print(_format_table(["metric", "value"], rows))
        else:
            for k, v in stats.items():
                print(f"{k}: {v}")
        return 0

    # Keyword mode (default behavior)
    if args.schema:
        print(json.dumps(_schema_for("keyword"), indent=2))
        return 0
    keyword = args.keyword if args.keyword is not None else "ERROR"
    try:
        count = count_pattern(
            args.logfile,
            keyword,
            use_regex=args.regex,
            ignore_case=args.ignore_case,
            whole_word=args.whole_word,
            since=since,
            until=until,
            include_untimestamped=args.include_untimestamped,
        )
    except re.error as exc:
        print(f"Invalid regex: {exc}", file=sys.stderr)
        return 2
    if format_mode == "json":
        print(json.dumps({"keyword": keyword, "count": count}, indent=2))
    elif format_mode == "table":
        print(_format_table(["keyword", "count"], [[keyword, count]]))
    else:
        print(f"Total '{keyword}' occurrences: {count}")
    return 0 if count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
