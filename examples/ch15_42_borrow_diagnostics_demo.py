"""Run the opt-in source diagnostics without changing compilation behavior."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qrvm.borrow_gate import check_borrow_source


def main():
    cases = (('valid', 'int x = 1;'), ('invalid', 'int x = missing;'), ('unsupported', 'print(1);'))
    for name, source in cases:
        result = check_borrow_source(source)
        print(f'{name}: {result.status.value} [{result.code}]')
    print('PASS: structured borrow diagnostics')


if __name__ == '__main__':
    main()
