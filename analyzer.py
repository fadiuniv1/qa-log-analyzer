import sys

def analyze_log(path: str, keyword: str = "ERROR") -> int:
    count = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if keyword in line:
                count += 1
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <logfile> [keyword]")
    else:
        log_path = sys.argv[1]
        keyword = sys.argv[2] if len(sys.argv) > 2 else "ERROR"
        result = analyze_log(log_path, keyword)
        print(f"Total '{keyword}' occurrences: {result}")
