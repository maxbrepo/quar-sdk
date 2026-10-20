"""Regression tests for post-run result filtering."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quar_main_result_filter", ROOT / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_crashes_can_be_inspected_without_reexecution():
    sources = [Path("1.vq"), Path("2.vq"), Path("3.vq")]
    outcomes = iter([("PASS", ""), ("CRASH", "traceback"), ("FAIL", "bad")])
    shown = []
    with patch.object(module, "execute_regression_source", side_effect=lambda _: next(outcomes)) as execute, \
         patch.object(module, "print_regression_results", side_effect=lambda rows, root: shown.append(list(rows))), \
         patch("builtins.input", side_effect=["3", "2", "0"]):
        module.run_regression_batch(sources, Path("."))
    assert execute.call_count == 3
    assert [row[1] for row in shown[1]] == ["CRASH"]
    assert [row[1] for row in shown[2]] == ["CRASH", "FAIL"]
    assert shown[1][0][2] == "traceback"


def test_expected_errors_are_not_unexpected_failures():
    records = [(Path("1.vq"), "EXPECTED ERROR", "expected"),
               (Path("2.vq"), "FAIL", "unexpected")]
    shown = []
    with patch.object(module, "print_regression_results", side_effect=lambda rows, root: shown.append(list(rows))), \
         patch("builtins.input", side_effect=["2", "5", "0"]):
        module.browse_regression_results(records, Path("."))
    assert [row[1] for row in shown[1]] == ["FAIL"]
    assert [row[1] for row in shown[2]] == ["EXPECTED ERROR"]
