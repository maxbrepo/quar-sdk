"""Remove superseded top-level Chapter 15 demo copies after relocation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
RELOCATED = ROOT / 'tests' / 'ch15_tests'


def main() -> None:
    """Remove old demos only if every relocated counterpart exists."""
    originals = sorted(EXAMPLES.glob('ch15_*.py'))
    missing = [p.name for p in originals if not (RELOCATED / p.name).is_file()]
    if missing:
        raise SystemExit(f'Refusing cleanup: missing relocated copies: {missing}')
    for original in originals:
        original.unlink()
    print(f'Removed {len(originals)} superseded Chapter 15 demo copies.')


if __name__ == '__main__':
    main()
