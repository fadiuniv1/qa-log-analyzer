QA Log Analyzer (Python)
A lightweight command-line tool for quickly analyzing log files.
It helps QA engineers, developers, and support teams surface errors, summarize severity levels, and group similar messages to reduce noise.

Features
- Count occurrences of a keyword (default: ERROR)
- Regex, case-insensitive, and whole-word keyword search
- Generate a severity summary (custom levels supported)
- Group similar log messages (Top-N with optional minimum count)
- File stats (total, empty, unique lines)
- Time-range filtering with timestamps (since/until)
- JSON schema output for CI ingestion
- Configurable summary exit codes
- Output format presets (text, json, table)
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

Whole-Word Keyword Match
```bash
python analyzer.py sample.log --keyword ERROR --whole-word
```

Regex Keyword Search (Case-Insensitive)
```bash
python analyzer.py sample.log --keyword "error|failed" --regex --ignore-case
```

Severity Summary
```bash
python analyzer.py sample.log --summary
```

Custom Summary Levels
```bash
python analyzer.py sample.log --summary --levels WARN,INFO
```

Custom Summary Exit Codes
```bash
python analyzer.py sample.log --summary --exit-codes ERROR=2,CRITICAL=3
```

JSON Output
```bash
python analyzer.py sample.log --summary --json
```

Format Presets
```bash
python analyzer.py sample.log --summary --format table
python analyzer.py sample.log --keyword ERROR --format json
```

Grouping (Top-N Similar Messages)
Reduce log noise by grouping repeated or similar messages.
Normalization removes timestamps, numbers, UUIDs, hex values, and paths so patterns become clear.

Usage
```bash
python analyzer.py sample.log --group
python analyzer.py sample.log --group --top 5
python analyzer.py sample.log --group --min-count 3
```

File Stats
```bash
python analyzer.py sample.log --stats
```

Time-Range Filtering
```bash
python analyzer.py sample.log --summary --since "2026-02-17T00:00:00" --until "2026-02-17T23:59:59"
python analyzer.py sample.log --keyword ERROR --since "2026-02-17" --include-untimestamped
```

JSON Schema Output
```bash
python analyzer.py sample.log --summary --schema
python analyzer.py sample.log --group --schema
```

Run Tests
```bash
python -m pytest -v
```

Notes
- The tool reads logs using UTF-8 and ignores invalid characters.
- sample.log is included as a small example file.
