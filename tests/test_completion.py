import argparse

import pytest

from analyzer import _MissingShtabAction, __version__, build_parser


def test_version_is_exposed():
    assert __version__ == "0.2.0"
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


def test_print_completion_requires_shtab_when_absent(monkeypatch):
    parser = argparse.ArgumentParser(prog="log-analyzer")
    parser.add_argument("logfile")
    parser.add_argument(
        "--print-completion",
        nargs="?",
        const="",
        metavar="SHELL",
        action=_MissingShtabAction,
    )
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--print-completion", "bash"])
    assert exc.value.code == 2


def test_optional_shtab_integration(monkeypatch):
    pytest.importorskip("shtab")
    parser = build_parser()
    actions = [a for a in parser._actions if "--print-completion" in a.option_strings]
    assert actions
    logfile = next(a for a in parser._actions if a.dest == "logfile")
    assert hasattr(logfile, "complete")
