"""Prototype shared/exclusive borrow access checks for Chapter 15.

Explicit events only: no source-language borrow semantics are implied.
"""
from dataclasses import dataclass
from enum import Enum
from qrvm.ownership_analysis import OwnershipError, OwnershipState


class BorrowMode(Enum):
    SHARED = 'shared'
    MUTABLE = 'mutable'


@dataclass(frozen=True)
class BorrowAccessState:
    ownership: OwnershipState
    modes: dict[str, BorrowMode]

    @classmethod
    def independent(cls, names):
        return cls(OwnershipState.independent(names), {})

    def __post_init__(self):
        if set(self.modes) != set(self.ownership.borrowers):
            raise OwnershipError('Every borrow must have an access mode')
        if any(not isinstance(mode, BorrowMode) for mode in self.modes.values()):
            raise OwnershipError('Invalid borrow mode')
        object.__setattr__(self, 'modes', dict(self.modes))

    def borrow(self, owner, reference, mode=BorrowMode.SHARED):
        if not isinstance(mode, BorrowMode):
            raise OwnershipError('Invalid borrow mode')
        if owner not in self.ownership.owners:
            raise OwnershipError('Borrow source must be an owner')
        active = [self.modes[ref] for ref, source in self.ownership.borrowers.items()
                  if source == owner]
        if mode == BorrowMode.MUTABLE and active:
            raise OwnershipError('Mutable borrow conflicts with active borrows')
        if mode == BorrowMode.SHARED and BorrowMode.MUTABLE in active:
            raise OwnershipError('Shared borrow conflicts with mutable borrow')
        ownership = self.ownership.borrow(owner, reference)
        return BorrowAccessState(ownership, {**self.modes, reference: mode})

    def release(self, reference):
        ownership = self.ownership.release(reference)
        modes = dict(self.modes)
        del modes[reference]
        return BorrowAccessState(ownership, modes)

    def read(self, name):
        self.ownership.require_access(name)
        if name in self.ownership.owners:
            if any(mode == BorrowMode.MUTABLE for ref, mode in self.modes.items()
                   if self.ownership.borrowers[ref] == name):
                raise OwnershipError('Owner read conflicts with mutable borrow')

    def write(self, name):
        self.ownership.require_access(name)
        if name in self.ownership.borrowers:
            if self.modes[name] != BorrowMode.MUTABLE:
                raise OwnershipError('Cannot write through shared borrow')
        elif name in self.ownership.owners:
            if name in self.ownership.borrowers.values():
                raise OwnershipError('Owner write conflicts with active borrow')

    def move(self, source, destination):
        return BorrowAccessState(self.ownership.move(source, destination), self.modes)

    def drop(self, owner):
        return BorrowAccessState(self.ownership.drop(owner), self.modes)
