# Chapter 01 — Primitive types, constants and conversions (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Primitive types, numeric compatibility, constants and checked conversions.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

The three source profiles are **inferred**, **mixed**, and **typed**. A C-like `int` is part of the familiar surface syntax; fixed-width numeric types also appear in the reference examples. Do not interpret these profiles as distinct runtime engines.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/01 primitives/057 byte alias.vq`

```vq
byte value = 255;
print(value);
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Interi a larghezza fissa e alias numerici, incluso `byte`.
- Diagnostici per overflow, underflow e perdita di precisione.
- Costanti dichiarate esplicitamente o inferite, divieto di riassegnazione.
- Inizializzazione di default e compatibilità numeriche conservative.
- Prime regole unificate per caratteri e testo.

These are historical documentation claims, not individually revalidated here.

## Profile comparison

| Profile | Representative declaration | Evidence |
|---|---|---|
| Inferred | `value = 10;` | Inferred chapter-1 examples |
| Mixed | `int count = 2;` and `result = count + 1;` | Mixed chapter-1 examples |
| Typed | `int count = 2;` | Typed examples |

An inferred-profile source file may still contain explicit types; the profile describes what is allowed, not a prohibition against type annotations.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
