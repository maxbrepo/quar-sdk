# Chapter 07 — Strings and Unicode (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Unicode strings, indexing, transformations and conversions.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/07 strings/125 unicode string.vq`

```vq
string text = "caffè";
print(text);
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Stringhe Unicode: lunghezza, indicizzazione, concatenazione e confronto.
- Sottostringhe, ricerca, sostituzione e trim.
- Conversione numeri/testo e diagnostici per stringhe numeriche non valide.
- Escape, iterazione Unicode, confronto ordinato e truthiness di stringa vuota.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
