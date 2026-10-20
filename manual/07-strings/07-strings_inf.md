# Chapter 07 — Strings and Unicode (Inferred profile)

> Visual Quar 0.0.4 beta · profile: `inferred` · documentation draft

## Scope

Unicode strings, indexing, transformations and conversions.

## Profile semantics

Local variables can be introduced by assignment when the selected profile permits inference. This does not mean that every declaration, function signature or advanced type can omit annotations.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.3/typed/07 strings/125 unicode string.vq`.

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
