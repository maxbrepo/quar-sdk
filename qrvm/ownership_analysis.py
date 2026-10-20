"""Experimental ownership facts, independent of Visual Quar language semantics.

Models exclusive owners and explicit move/borrow events. It does not decide
which source-language expressions trigger those events.
"""
from dataclasses import dataclass
from enum import Enum


class OwnershipError(ValueError):
    """An operation violates the prototype ownership rules."""


class OwnershipKind(Enum):
    OWNED = 'owned'
    MOVED = 'moved'


@dataclass(frozen=True)
class OwnershipState:
    """Immutable ownership snapshot; borrowers map names to their owner."""
    owners: dict[str, OwnershipKind]
    borrowers: dict[str, str]

    @classmethod
    def independent(cls, names):
        names = list(names)
        if len(names) != len(set(names)):
            raise OwnershipError('Duplicate owner')
        return cls({name: OwnershipKind.OWNED for name in names}, {})

    def __post_init__(self):
        if set(self.owners) & set(self.borrowers):
            raise OwnershipError('An identifier cannot be both owner and borrower')
        if any(owner not in self.owners for owner in self.borrowers.values()):
            raise OwnershipError('Borrowed owner must exist')
        if any(self.owners[owner] != OwnershipKind.OWNED for owner in self.borrowers.values()):
            raise OwnershipError('Cannot borrow from moved owner')
        object.__setattr__(self, 'owners', dict(self.owners))
        object.__setattr__(self, 'borrowers', dict(self.borrowers))

    def require_access(self, name):
        if name in self.borrowers:
            return
        if self.owners.get(name) != OwnershipKind.OWNED:
            raise OwnershipError(f'Value is unavailable: {name}')

    def borrow(self, owner, reference):
        self.require_access(owner)
        if owner not in self.owners:
            raise OwnershipError('Borrow source must be an owner')
        if reference in self.owners or reference in self.borrowers:
            raise OwnershipError('Borrow name already in use')
        return OwnershipState(self.owners, {**self.borrowers, reference: owner})

    def release(self, reference):
        if reference not in self.borrowers:
            raise OwnershipError('Unknown borrow')
        borrowers = dict(self.borrowers)
        del borrowers[reference]
        return OwnershipState(self.owners, borrowers)

    def move(self, source, destination):
        self.require_access(source)
        if source not in self.owners:
            raise OwnershipError('Only owned values can move')
        if destination in self.owners or destination in self.borrowers:
            raise OwnershipError('Move destination already in use')
        if source in self.borrowers.values():
            raise OwnershipError('Cannot move while borrowed')
        owners = dict(self.owners)
        owners[source] = OwnershipKind.MOVED
        owners[destination] = OwnershipKind.OWNED
        return OwnershipState(owners, self.borrowers)

    def drop(self, owner):
        self.require_access(owner)
        if owner not in self.owners:
            raise OwnershipError('Only an owner can be dropped')
        if owner in self.borrowers.values():
            raise OwnershipError('Cannot drop while borrowed')
        owners = dict(self.owners)
        owners[owner] = OwnershipKind.MOVED
        return OwnershipState(owners, self.borrowers)
