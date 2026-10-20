"""Combined lexical lifetime and borrow access prototype.

Explicit analysis events only; no source-level move or borrow rules are assumed.
"""
from dataclasses import dataclass
from qrvm.borrow_access import BorrowAccessState, BorrowMode
from qrvm.lifetime_analysis import LifetimeState
from qrvm.ownership_analysis import OwnershipError


@dataclass(frozen=True)
class BorrowLifetimeState:
    lifetime: LifetimeState
    modes: dict[str, BorrowMode]

    @classmethod
    def empty(cls):
        return cls(LifetimeState.empty(), {})

    def __post_init__(self):
        # The borrow-access checker validates mode completeness and consistency.
        BorrowAccessState(self.lifetime.ownership, self.modes)
        object.__setattr__(self, 'modes', dict(self.modes))

    def _access(self):
        return BorrowAccessState(self.lifetime.ownership, self.modes)

    def enter(self, scope):
        return BorrowLifetimeState(self.lifetime.enter(scope), self.modes)

    def declare(self, name):
        return BorrowLifetimeState(self.lifetime.declare(name), self.modes)

    def borrow(self, owner, reference, mode=BorrowMode.SHARED):
        # Validate conflicts first, then attach lexical lifetime information.
        self._access().borrow(owner, reference, mode)
        return BorrowLifetimeState(self.lifetime.borrow(owner, reference),
                                   {**self.modes, reference: mode})

    def release(self, reference):
        self._access().release(reference)
        modes = dict(self.modes)
        del modes[reference]
        return BorrowLifetimeState(self.lifetime.release(reference), modes)

    def read(self, name):
        self._access().read(name)

    def write(self, name):
        self._access().write(name)

    def move(self, source, destination):
        self._access().move(source, destination)
        return BorrowLifetimeState(self.lifetime.move(source, destination), self.modes)

    def drop(self, owner):
        self._access().drop(owner)
        return BorrowLifetimeState(
            LifetimeState(self.lifetime.ownership.drop(owner),
                          self.lifetime.scopes, self.lifetime.declared), self.modes)

    def exit(self):
        if len(self.lifetime.scopes) == 1:
            raise OwnershipError('Cannot exit root scope')
        expired = {name for name, scope in self.lifetime.declared.items()
                   if scope == self.lifetime.scopes[-1]}
        lifetime = self.lifetime.exit()
        return BorrowLifetimeState(lifetime, {ref: mode for ref, mode in self.modes.items()
                                              if ref not in expired})
