# Kart 0.0.1 — Chapter 14.5: Shared dependencies

Kart resolves local transitive dependencies once per canonical folder.
A diamond dependency graph can share a single local package if all incoming
version constraints match the package's installed version.

Kart reports a version conflict when a requested version range is not met.
It rejects two different folders claiming the same package identity,
and it detects dependency cycles.

This version does not download or select alternative versions, and does
not support remote registries, Git dependencies, or prerelease comparison.

Run tests from the Quar SDK root:

    python3 -m unittest discover -s tests -p 'test_kart*.py' -v

Only `kart/core.py` and new test/documentation files are included in this patch.
