# Chapter 03 — Conditions and selection (Mixed profile)

> Visual Quar 0.0.4 beta · profile: `mixed` · documentation draft

## Scope

Conditional branches, truthiness and case selection.

## Profile semantics

The mixed profile permits a combination of explicit typed declarations and inferred local bindings where implemented.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.3/typed/03 conditions/077 nested conditions.vq`.

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
