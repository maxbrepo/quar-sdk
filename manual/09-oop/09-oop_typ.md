# Chapter 09 — Object-oriented programming (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Classes, constructors, fields and methods.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.4/typed/09 oop/161 class declaration.vq`

```vq
class Player { i32 health; }
print(1);
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Definizione delle classi.
- Costruttore di default e parametrizzato.
- Inizializzazione dei campi, accesso `this`.
- Metodi `void` e con valore di ritorno.
- Istanziazione indipendente e diagnostici su campi/argomenti del costruttore.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
