#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from collections import defaultdict
from typing import Iterable, List, Tuple

DEFAULT_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def iter_lines(path: str):
    if path == "-":
        for raw in sys.stdin:
            yield raw.rstrip("\n")
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            yield line.rstrip("\n")


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
) -> int:
    rx = _compile_keyword(pattern, use_regex, ignore_case, whole_word)
    return sum(1 for line in iter_lines(path) if rx.search(line))


def _compile_levels(levels: Iterable[str]) -> List[Tuple[str, re.Pattern]]:
    compiled = []
    for lvl in levels:
        if not lvl:
            continue
        compiled.append((lvl, re.compile(rf"\b{re.escape(lvl)}\b")))
    return compiled


def severity_summary(path: str, levels=DEFAULT_LEVELS) -> dict:
    counts = Counter()
    compiled_levels = _compile_levels(levels)
    for line in iter_lines(path):
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


def group_messages(path: str, top_n: int = 10, min_count: int = 1) -> List[Tuple[int, str, int, int]]:
    """
    Returns a list of tuples: (count, sample_line, first_seen_line_no, last_seen_line_no)
    Ordered by count descending, limited to top_n.
    """
    counts = Counter()
    samples = {}
    first_seen = {}
    last_seen = {}
    for i, raw in enumerate(iter_lines(path), start=1):
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


def file_stats(path: str) -> dict:
    total = 0
    empty = 0
    unique_lines = set()
    for line in iter_lines(path):
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
    p.add_argument("--json", action="store_true", help="Output as JSON (useful for automation/CI)")
    return p


def main() -> int:
    args = build_parser().parse_args()

    # Grouping mode
    if args.group:
        groups = group_messages(args.logfile, top_n=args.top, min_count=args.min_count)
        if args.json:
            out = [
                {"count": c, "sample": s, "first_line": f, "last_line": l} for c, s, f, l in groups
            ]
            print(json.dumps(out, indent=2))
        else:
            for c, s, f, l in groups:
                print(f"{c}x | lines {f}-{l} | {s}")
        return 0

    # Severity summary mode
    if args.summary:
        levels = DEFAULT_LEVELS
        if args.levels is not None:
            try:
                levels = _parse_levels(args.levels)
            except ValueError as exc:
                print(f"Invalid levels: {exc}", file=sys.stderr)
                return 2
        result = severity_summary(args.logfile, levels=levels)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        # exit code: 0 if no ERROR/CRITICAL, else 1
        return 0 if (result.get("ERROR", 0) == 0 and result.get("CRITICAL", 0) == 0) else 1

    # Stats mode
    if args.stats:
        stats = file_stats(args.logfile)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            for k, v in stats.items():
                print(f"{k}: {v}")
        return 0

    # Keyword mode (default behavior)
    keyword = args.keyword if args.keyword is not None else "ERROR"
    try:
        count = count_pattern(
            args.logfile,
            keyword,
            use_regex=args.regex,
            ignore_case=args.ignore_case,
            whole_word=args.whole_word,
        )
    except re.error as exc:
        print(f"Invalid regex: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"keyword": keyword, "count": count}, indent=2))
    else:
        print(f"Total '{keyword}' occurrences: {count}")
    return 0 if count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
