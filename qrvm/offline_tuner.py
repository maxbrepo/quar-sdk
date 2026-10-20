"""Opt-in offline benchmark comparison; no live mutation or auto tuning."""
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns
from typing import Callable, Mapping


@dataclass(frozen=True)
class TuningResult:
    name: str
    median_ns: int
    samples_ns: tuple[int, ...]


def compare_variants(variants: Mapping[str, Callable[[], object]], repeats: int = 5):
    """Measure explicitly supplied equivalent variants; return fastest median first.

    Caller must guarantee semantic equivalence and representative inputs.
    """
    if not variants or not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1 or repeats > 1000:
        raise ValueError('Expected variants and 1..1000 repetitions')
    if any(not name or not callable(fn) for name, fn in variants.items()):
        raise ValueError('Variant names and callables must be valid')
    results = []
    for name, fn in variants.items():
        samples = []
        for _ in range(repeats):
            start = perf_counter_ns()
            fn()
            samples.append(perf_counter_ns() - start)
        results.append(TuningResult(name, int(median(samples)), tuple(samples)))
    return tuple(sorted(results, key=lambda item: (item.median_ns, item.name)))
