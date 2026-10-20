"""Experimental lexical lifetime checks for explicitly modeled borrow events.

This analysis is independent of source syntax and runtime memory management.
"""
from dataclasses import dataclass
from qrvm.ownership_analysis import OwnershipError, OwnershipState


@dataclass(frozen=True)
class LifetimeState:
    ownership: OwnershipState
    scopes: tuple[str, ...]
    declared: dict[str, str]

    @classmethod
    def empty(cls):
        return cls(OwnershipState.independent([]), ('root',), {})

    def __post_init__(self):
        if not self.scopes or len(set(self.scopes)) != len(self.scopes):
            raise OwnershipError('Invalid scope stack')
        if set(self.declared) != set(self.ownership.owners) | set(self.ownership.borrowers):
            raise OwnershipError('Every binding needs a lifetime scope')
        if any(scope not in self.scopes for scope in self.declared.values()):
            raise OwnershipError('Binding declared outside active scopes')
        for ref, owner in self.ownership.borrowers.items():
            if self.scopes.index(self.declared[owner]) > self.scopes.index(self.declared[ref]):
                raise OwnershipError('Borrow outlives its owner scope')
        object.__setattr__(self, 'declared', dict(self.declared))

    def enter(self, scope):
        if not scope or scope in self.scopes:
            raise OwnershipError('Scope must be unique and nonempty')
        return LifetimeState(self.ownership, (*self.scopes, scope), self.declared)

    def declare(self, name):
        if name in self.declared:
            raise OwnershipError('Binding already declared')
        owners = dict(self.ownership.owners)
        owners[name] = self.ownership_kind()
        return LifetimeState(OwnershipState(owners, self.ownership.borrowers), self.scopes,
                             {**self.declared, name: self.scopes[-1]})

    @staticmethod
    def ownership_kind():
        from qrvm.ownership_analysis import OwnershipKind
        return OwnershipKind.OWNED

    def borrow(self, owner, reference):
        if owner not in self.declared:
            raise OwnershipError('Unknown owner')
        ownership = self.ownership.borrow(owner, reference)
        return LifetimeState(ownership, self.scopes,
                             {**self.declared, reference: self.scopes[-1]})

    def release(self, reference):
        ownership = self.ownership.release(reference)
        declared = dict(self.declared)
        del declared[reference]
        return LifetimeState(ownership, self.scopes, declared)

    def move(self, source, destination):
        ownership = self.ownership.move(source, destination)
        return LifetimeState(ownership, self.scopes,
                             {**self.declared, destination: self.scopes[-1]})

    def exit(self):
        if len(self.scopes) == 1:
            raise OwnershipError('Cannot exit root scope')
        scope = self.scopes[-1]
        expired = {name for name, declared_scope in self.declared.items() if declared_scope == scope}
        # References declared in outer scopes must not point into the exiting scope.
        if any(ref not in expired and owner in expired
               for ref, owner in self.ownership.borrowers.items()):
            raise OwnershipError('Reference would outlive its owner')
        owners = {name: kind for name, kind in self.ownership.owners.items()
                  if name not in expired}
        borrowers = {ref: owner for ref, owner in self.ownership.borrowers.items()
                     if ref not in expired}
        declared = {name: owner_scope for name, owner_scope in self.declared.items()
                    if name not in expired}
        return LifetimeState(OwnershipState(owners, borrowers), self.scopes[:-1], declared)

    def require_access(self, name):
        self.ownership.require_access(name)
