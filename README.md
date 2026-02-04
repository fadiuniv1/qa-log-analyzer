# QA Log Analyzer (Python)

Small CLI tool that scans a log file and counts lines containing a keyword (default: `ERROR`).

## Quick start

```bash
python analyzer.py sample.log
```
## Use a custom keyword
```bash
python analyzer.py sample.log --keyword WARNING
```
## Help
```bash
python analyzer.py -h
```
## Run tests
```bash
python -m pytest -v
```
## *notes
The tool reads text logs using UTF-8 (ignores invalid characters).

sample.log is included as a tiny example file.