# Chapter 08 — Structured types (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Structs, records, enums, tuples, aliases and pattern matching.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/08 structured types/148 tuple basic.vq`

```vq
tuple pair = (10, "hello");
print(pair);
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- `struct` mutabile e `record` immutabile.
- `enum` e type aliases, comprese catene di alias.
- Tuple e destrutturazione con controllo dell’arità.
- Valori associati agli enum e varianti con payload.
- `match` su varianti, binding, default, copertura esaustiva e rilevamento duplicati.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
