from analyzer import (
    count_pattern,
    severity_summary,
    group_messages,
    file_stats,
    _parse_exit_codes,
    _schema_for,
    _format_table,
)
import tempfile
import os
from datetime import datetime


def _tempfile_with(content: str) -> str:
    fd, path = tempfile.mkstemp(text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_count_keyword_default_like_error():
    content = "INFO ok\nERROR one\nERROR two\n"
    path = _tempfile_with(content)
    try:
        assert count_pattern(path, "ERROR") == 2
    finally:
        os.remove(path)


def test_custom_keyword():
    content = "INFO ok\nFOO first\nFOO second\n"
    path = _tempfile_with(content)
    try:
        assert count_pattern(path, "FOO") == 2
    finally:
        os.remove(path)


def test_severity_summary_counts_levels():
    content = (
        "DEBUG a\nINFO start\nWARNING low disk\nERROR timeout\nCRITICAL boom\nINFO end\n"
    )
    path = _tempfile_with(content)
    try:
        summary = severity_summary(path)
        assert summary["DEBUG"] == 1
        assert summary["INFO"] == 2
        assert summary["WARNING"] == 1
        assert summary["ERROR"] == 1
        assert summary["CRITICAL"] == 1
    finally:
        os.remove(path)


def test_regex_ignore_case():
    content = "INFO Start\nerror one\nError two\n"
    path = _tempfile_with(content)
    try:
        assert count_pattern(path, r"error", use_regex=True, ignore_case=True) == 2
    finally:
        os.remove(path)


def test_whole_word_literal():
    content = "ERROR one\nERRORX two\nERROR three\n"
    path = _tempfile_with(content)
    try:
        assert count_pattern(path, "ERROR", whole_word=True) == 2
    finally:
        os.remove(path)
def test_grouping_top_limit():
    content = "ERROR A\nERROR A\nERROR B\n"
    path = _tempfile_with(content)
    try:
        groups = group_messages(path, top_n=1)
        assert len(groups) == 1
        assert groups[0][0] == 2      # count
        assert "ERROR A" in groups[0][1]
    finally:
        os.remove(path)


def test_grouping_min_count():
    content = "ERROR A\nERROR A\nERROR B\n"
    path = _tempfile_with(content)
    try:
        groups = group_messages(path, top_n=10, min_count=2)
        assert len(groups) == 1
        assert groups[0][0] == 2
    finally:
        os.remove(path)


def test_summary_custom_levels():
    content = "WARN low\nINFO ok\nWARN high\n"
    path = _tempfile_with(content)
    try:
        summary = severity_summary(path, levels=("WARN", "INFO"))
        assert summary["WARN"] == 2
        assert summary["INFO"] == 1
    finally:
        os.remove(path)


def test_file_stats():
    content = "a\n\nb\nb\n"
    path = _tempfile_with(content)
    try:
        stats = file_stats(path)
        assert stats["total_lines"] == 4
        assert stats["empty_lines"] == 1
        assert stats["non_empty_lines"] == 3
        assert stats["unique_lines"] == 3
    finally:
        os.remove(path)


def test_time_filtering_and_untimestamped():
    content = (
        "2026-02-16 10:00:00 INFO a\n"
        "2026-02-17 10:00:00 ERROR b\n"
        "no ts ERROR\n"
    )
    path = _tempfile_with(content)
    try:
        since = datetime.fromisoformat("2026-02-17T00:00:00")
        assert count_pattern(path, "ERROR", since=since) == 1
        assert count_pattern(path, "ERROR", since=since, include_untimestamped=True) == 2
    finally:
        os.remove(path)


def test_parse_exit_codes():
    mapping = _parse_exit_codes("ERROR=2,CRITICAL=3")
    assert mapping["ERROR"] == 2
    assert mapping["CRITICAL"] == 3


def test_schema_group_shape():
    schema = _schema_for("group")
    assert schema["type"] == "array"
    assert "items" in schema


def test_format_table_basic():
    table = _format_table(["a", "b"], [[1, "two"]])
    lines = table.splitlines()
    assert lines[0].startswith("a")
    assert "b" in lines[0]
    assert "1" in lines[2]
    assert "two" in lines[2]
