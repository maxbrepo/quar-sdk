# Chapter 15 — Memory safety (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Memory-safety diagnostics and experimental borrow/lifetime checks.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

This chapter documents an experimental safety foundation. Full reference lifetimes, deterministic cleanup, regions/arenas and unsafe FFI guarantees are not established.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.4/typed/15 memory safety/239 borrow source valid.vq`

```vq
int counter = 1;
if (true) {
    int local = counter;
    counter = local + 1;
} else {
    counter = 3;
}
int result = counter;
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
