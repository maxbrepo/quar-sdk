# Chapter 03 — Conditions and selection (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Conditional branches, truthiness and case selection.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/03 conditions/077 nested conditions.vq`

```vq
i32 level = 2;
bool ready = true;
if (level > 0) {
    if (ready) {
        print("ready");
    }
}
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- `if`, `else if` e condizioni annidate.
- Truthiness per numeri e testo.
- Selezione strutturata `case` con ramo default.
- Compatibilità con `switch` precedente.
- Rifiuto di valori `case` duplicati e default ripetuti.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
