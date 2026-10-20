# Chapter 13 — Modules (Visual Quar 0.0.4)

Five independent projects, numbered 234–238. Run `main.vq` from each project root using the existing Module Loader + QRVM pipeline. Supporting `.vq` files are imported, not executed separately.

- 234: simple import and qualified call (42)
- 235: import alias (42)
- 236: nested module path (49)
- 237: two imported modules and nested calls (42)
- 238: module function calling another function in the same module (42)

These examples require Chapter 13 Module Loader and the Chapter 14.21 parser support for qualified calls inside expressions. No Kart manifest is required for local module imports.
