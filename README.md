QA Log Analyzer (Python)
A lightweight command-line tool for quickly analyzing log files.
It helps QA engineers, developers, and support teams surface errors, summarize severity levels, and group similar messages to reduce noise.

Features
- Count occurrences of a keyword (default: ERROR)
- Regex and case-insensitive keyword search
- Generate a severity summary
- Group similar log messages (Top-N)
- JSON output support
- UTF-8 tolerant log reading
- Simple, fast, dependency-free

Quick Start
```bash
python analyzer.py sample.log
```

Use a Custom Keyword
```bash
python analyzer.py sample.log --keyword WARNING
```

Regex Keyword Search (Case-Insensitive)
```bash
python analyzer.py sample.log --keyword "error|failed" --regex --ignore-case
```

Severity Summary
```bash
python analyzer.py sample.log --summary
```

JSON Output
```bash
python analyzer.py sample.log --summary --json
```

Grouping (Top-N Similar Messages)
Reduce log noise by grouping repeated or similar messages.
Normalization removes timestamps, numbers, UUIDs, hex values, and paths so patterns become clear.

Usage
```bash
python analyzer.py sample.log --group
python analyzer.py sample.log --group --top 5
```

Run Tests
```bash
python -m pytest -v
```

Notes
- The tool reads logs using UTF-8 and ignores invalid characters.
- sample.log is included as a small example file.
