from analyzer import count_keyword, severity_summary, group_messages
import tempfile
import os


def _tempfile_with(content: str) -> str:
    fd, path = tempfile.mkstemp(text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_count_keyword_default_like_error():
    content = "INFO ok\nERROR one\nERROR two\n"
    path = _tempfile_with(content)
    try:
        assert count_keyword(path, "ERROR") == 2
    finally:
        os.remove(path)


def test_custom_keyword():
    content = "INFO ok\nFOO first\nFOO second\n"
    path = _tempfile_with(content)
    try:
        assert count_keyword(path, "FOO") == 2
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