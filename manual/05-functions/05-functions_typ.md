# Chapter 05 — Functions and parameters (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Typed functions, returns, recursion, defaults and named arguments.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Function return types and parameter types are explicit in the available examples. An inferred local variable does not imply that inferred function signatures are implemented.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/05 functions/099 void function.vq`

```vq
void show(i32 value) {
    print(value);
    return;
}

show(99);
```

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
