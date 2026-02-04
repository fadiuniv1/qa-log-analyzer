from analyzer import analyze_log
import tempfile
import os

def test_count_errors():
    content = "INFO ok\nERROR one\nERROR two\n"

    fd, path = tempfile.mkstemp(text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        assert analyze_log(path) == 2
    finally:
        os.remove(path)
def test_custom_keyword():
    content = "INFO ok\nFOO first\nFOO second\n"
    fd, path = tempfile.mkstemp(text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        assert analyze_log(path, "FOO") == 2
    finally:
        os.remove(path)
