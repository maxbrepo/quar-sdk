"""Run the opt-in source borrow analysis on two real .vq files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qrvm.borrow_source import analyze_borrow_file
from qrvm.ownership_analysis import OwnershipError


def main():
    root = Path(__file__).resolve().parent / '0.0.4' / 'typed' / '15 memory safety'
    valid = root / '239 borrow source valid.vq'
    invalid = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'ch15_40' / 'invalid_expired_scope.vq'
    result = analyze_borrow_file(valid)
    print(f'PASS: parsed and analyzed {len(result.statements)} source statements')
    try:
        analyze_borrow_file(invalid)
    except OwnershipError as error:
        print(f'Expected scope conflict: {error}')
    else:
        raise AssertionError('Expired variable was accepted')
    print('PASS: source-level scope conflict rejected')


if __name__ == '__main__':
    main()
