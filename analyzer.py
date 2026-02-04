def analyze_log(path: str) -> int:
    errors = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "ERROR" in line:
                errors += 1
    return errors


if __name__ == "__main__":
    path = "sample.log"
    count = analyze_log(path)
    print(f"Total ERRORs: {count}")
