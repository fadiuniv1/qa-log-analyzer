import argparse


def analyze_log(path: str, keyword: str = "ERROR") -> int:
    count = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if keyword in line:
                count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="log-analyzer",
        description="Scan a log file and count lines containing a keyword.",
        epilog="Example: python analyzer.py sample.log --keyword ERROR",
    )
    parser.add_argument(
        "logfile",
        help="Path to the log file to analyze",
    )
    parser.add_argument(
        "-k",
        "--keyword",
        default="ERROR",
        help="Keyword to search for (default: ERROR)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result = analyze_log(args.logfile, args.keyword)
    print(f"Total '{args.keyword}' occurrences: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
