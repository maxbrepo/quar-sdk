# Chapter 12 — Error handling (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Error propagation, chaining, assertions and panic.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.4/typed/12 error handling/221 assertion success.vq`

```vq
assert(true); print("ok");
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- 12A: `try/catch`, `throw` e campo `error.message`.
- 12B: `throw ... from error` e catena in `error.cause`.
- 12C: `assert(bool)` e `error.trace` con nomi delle funzioni.
- 12D: `panic(string)` fatale, non intercettabile da `catch`, distinto da `exit`.
- `with` deve liberare le risorse durante l’unwinding; nessun recovery generale da panic.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
