# Chapter 05 — Functions and parameters (Mixed profile)

> Visual Quar 0.0.4 beta · profile: `mixed` · documentation draft

## Scope

Typed functions, returns, recursion, defaults and named arguments.

## Profile semantics

The mixed profile permits a combination of explicit typed declarations and inferred local bindings where implemented.

Function return types and parameter types are explicit in the available examples. An inferred local variable does not imply that inferred function signatures are implemented.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.3/typed/05 functions/099 void function.vq`.

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Dichiarazione di funzione con tipo di ritorno, inclusi `void` e ricorsione.
- Parametri multipli e default.
- Argomenti con nome e combinazione posizionale/nominata nella specifica e negli esempi.
- Controllo di argomenti richiesti, sconosciuti, ripetuti e default non validi.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
