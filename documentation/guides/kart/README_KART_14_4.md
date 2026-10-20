# Kart 0.0.1 — Chapter 14.4

Copy the `kart/` directory into the Quar SDK root, replacing the three corresponding Python files. Add `tests/test_kart_constraints.py` to your tests folder. No changes to `main.py`.

Use Python 3.11 or later.

Example `kart.toml`:

```toml
[package]
name = "demo_app"
version = "0.0.1"

[dependencies]
mathlib = { path = "../mathlib", version = ">=1.2.0,<2.0.0" }
```

Supported version constraints: exact `1.2.0`, `==1.2.0`, `>=1.2.0`, `>1.2.0`, `<=1.2.0`, `<1.2.0`, comma-separated conjunctions, `*`. Prerelease comparisons, registry packages, Git packages, and version selection across multiple candidates are not implemented.

Commands:

- `python3 main.py kart --version`
- `python3 -m kart --version`
- `python3 -m kart info <project-dir>`
- `python3 -m kart lock <project-dir>`
- `python3 -m unittest discover -s tests -p 'test_kart_constraints.py' -v`

The lockfile is still an experimental JSON format; no network activity is performed.
