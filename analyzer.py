import argparse
import json
from collections import Counter


DEFAULT_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def iter_lines(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            yield line.rstrip("\n")


def count_keyword(path: str, keyword: str) -> int:
    return sum(1 for line in iter_lines(path) if keyword in line)


def severity_summary(path: str, levels=DEFAULT_LEVELS) -> dict[str, int]:
    counts = Counter()
    for line in iter_lines(path):
        for lvl in levels:
            # simple rule: if the level token appears in the line, count it
            if lvl in line:
                counts[lvl] += 1
                break
    # return a stable dict with all levels (even if 0)
    return {lvl: int(counts.get(lvl, 0)) for lvl in levels}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="log-analyzer",
        description="Analyze a log file: count keyword occurrences or produce a severity summary.",
        epilog="Examples: python analyzer.py sample.log --keyword ERROR | python analyzer.py sample.log --summary --json",
    )
    p.add_argument("logfile", help="Path to the log file to analyze")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-k", "--keyword", default="ERROR", help="Keyword to search for (default: ERROR)")
    mode.add_argument("-s", "--summary", action="store_true", help="Show severity summary (DEBUG/INFO/WARNING/ERROR/CRITICAL)")

    p.add_argument("--json", action="store_true", help="Output as JSON (useful for automation/CI)")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.summary:
        result = severity_summary(args.logfile)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        # exit code: 0 if no ERROR/CRITICAL, else 1
        return 0 if (result.get("ERROR", 0) == 0 and result.get("CRITICAL", 0) == 0) else 1

    # keyword mode (default)
    count = count_keyword(args.logfile, args.keyword)
    if args.json:
        print(json.dumps({"keyword": args.keyword, "count": count}, indent=2))
    else:
        print(f"Total '{args.keyword}' occurrences: {count}")
    return 0 if count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
