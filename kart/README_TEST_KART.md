# Visual Quar 0.0.4 — Kart 0.0.1 — Chapter 14.3

This incremental archive contains **new example and test files only**. Keep your existing `kart/` and `main.py` from Chapter 14.2.

## Requirements

Python 3.11 or newer, from the Quar SDK root directory.

## Manual checks

1. `python3 main.py kart info examples/kart_local_demo/app`
2. `python3 main.py kart lock examples/kart_local_demo/app`
3. Inspect `examples/kart_local_demo/app/kart.lock`.
4. `python3 -m unittest discover -s tests -p 'test_kart_local.py' -v`

The test suite creates isolated temporary projects and does not modify the example manifests. `kart lock` writes `kart.lock` into the example app folder.

## Scope

This tests manifest handling and local dependency resolution. It does **not** yet install a library, resolve version constraints, or connect library code to the Visual Quar compiler.

## Versioning

Kart official version: 0.0.1. Chapter 14.3 is a work-block label, not a release version.
