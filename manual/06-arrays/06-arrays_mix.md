# Chapter 06 — Arrays (Mixed profile)

> Visual Quar 0.0.4 beta · profile: `mixed` · documentation draft

## Scope

Static and dynamic arrays, indexing and multidimensional structures.

## Profile semantics

The mixed profile permits a combination of explicit typed declarations and inferred local bindings where implemented.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.3/typed/06 arrays/119 dynamic empty array.vq`.

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Array statici, lettura, assegnazione e lunghezza.
- Iterazione indicizzata e array multidimensionali.
- Diagnostici per indici fuori intervallo in lettura e scrittura.
- Prime forme di array dinamici e relativi controlli.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
