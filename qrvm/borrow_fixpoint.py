"""Finite-state loop closure for explicit borrow events (not source integration).

Explores zero or more iterations. A loop is accepted only when the reachable
abstract states reach a fixed point within the configured state budget.
"""
from dataclasses import dataclass
from typing import Callable
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_lifetime import BorrowLifetimeState
from qrvm.ownership_analysis import OwnershipError


def state_key(state: BorrowLifetimeState) -> tuple:
    """Canonical, hashable representation of a borrow/lifetime snapshot."""
    lifetime = state.lifetime
    ownership = lifetime.ownership
    return (tuple(sorted((name, kind.value) for name, kind in ownership.owners.items())),
            tuple(sorted(ownership.borrowers.items())),
            tuple(sorted((name, mode.value) for name, mode in state.modes.items())),
            lifetime.scopes, tuple(sorted(lifetime.declared.items())))


@dataclass(frozen=True)
class LoopResult:
    flow: BorrowFlow
    iterations: int  # Number of body applications, not runtime loop iterations.
    reachable_states: int


def loop_fixpoint(initial: BorrowFlow,
                  body: Callable[[BorrowFlow], BorrowFlow],
                  max_states: int = 256) -> LoopResult:
    """Compute the exact reachable closure of finite abstract loop states.

    Includes the zero-iteration path. The body must preserve the scope stack
    and return BorrowFlow. Unbounded state growth fails closed rather than
    silently treating an incomplete exploration as safe.
    """
    if not isinstance(initial, BorrowFlow):
        raise OwnershipError('Loop entry must be a BorrowFlow')
    if not callable(body):
        raise OwnershipError('Loop body must be callable')
    if isinstance(max_states, bool) or not isinstance(max_states, int) or max_states < 1:
        raise OwnershipError('State budget must be a positive integer')
    states = {state_key(path): path for path in initial.paths}
    if len(states) > max_states:
        raise OwnershipError('Loop state budget exceeded')
    frontier = list(states.values())
    applications = 0
    scopes = initial.paths[0].lifetime.scopes
    while frontier:
        next_frontier = []
        for path in frontier:
            result = body(BorrowFlow((path,)))
            applications += 1
            if not isinstance(result, BorrowFlow):
                raise OwnershipError('Loop body must return a BorrowFlow')
            for successor in result.paths:
                if successor.lifetime.scopes != scopes:
                    raise OwnershipError('Loop body must preserve lexical scopes')
                key = state_key(successor)
                if key not in states:
                    if len(states) >= max_states:
                        raise OwnershipError('Loop state budget exceeded; convergence not proven')
                    states[key] = successor
                    next_frontier.append(successor)
        frontier = next_frontier
    return LoopResult(BorrowFlow(tuple(states.values())), applications, len(states))
