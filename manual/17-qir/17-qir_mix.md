# Chapter 17 — Intermediate representation (QIR) (Mixed profile)

> Visual Quar 0.0.4 beta · profile: `mixed` · documentation draft

## Scope

Compiler intermediate representation, type normalization and pipeline parity.

## Profile semantics

The mixed profile permits a combination of explicit typed declarations and inferred local bindings where implemented.

This chapter primarily describes compiler/toolchain internals rather than introducing a separate surface-language grammar.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
