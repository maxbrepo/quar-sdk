"""Path-sensitive borrow-flow foundation for conditional branches and bounded loops.

Events are explicit analyzer operations, not Visual Quar source-language syntax.
Every feasible path must permit an operation before it is considered safe.
"""
from dataclasses import dataclass
from typing import Callable
from qrvm.borrow_lifetime import BorrowLifetimeState
from qrvm.ownership_analysis import OwnershipError


@dataclass(frozen=True)
class BorrowFlow:
    paths: tuple[BorrowLifetimeState, ...]

    @classmethod
    def empty(cls):
        return cls((BorrowLifetimeState.empty(),))

    def __post_init__(self):
        if not self.paths:
            raise OwnershipError('Flow requires at least one feasible path')
        if any(not isinstance(path, BorrowLifetimeState) for path in self.paths):
            raise OwnershipError('Invalid borrow flow path')
        # Alternative paths must have a common lexical scope stack.
        scopes = self.paths[0].lifetime.scopes
        if any(path.lifetime.scopes != scopes for path in self.paths):
            raise OwnershipError('Cannot join different lexical scope stacks')

    def apply(self, operation: Callable[[BorrowLifetimeState], BorrowLifetimeState]):
        """Apply an event to every path, rejecting it if any path is unsafe."""
        updated = tuple(operation(path) for path in self.paths)
        return BorrowFlow(updated)

    def check(self, operation: Callable[[BorrowLifetimeState], None]):
        """Validate an access on every path without changing the flow."""
        for path in self.paths:
            operation(path)

    def branch(self, then_branch: Callable[['BorrowFlow'], 'BorrowFlow'],
               else_branch: Callable[['BorrowFlow'], 'BorrowFlow']):
        """Explore both branches independently and retain their alternatives."""
        left = then_branch(self)
        right = else_branch(self)
        if not isinstance(left, BorrowFlow) or not isinstance(right, BorrowFlow):
            raise OwnershipError('Branch must return a BorrowFlow')
        return BorrowFlow(left.paths + right.paths)

    def loop_once(self, body: Callable[['BorrowFlow'], 'BorrowFlow']):
        """Model zero or one iteration, NOT an arbitrary repeating loop."""
        result = body(self)
        if not isinstance(result, BorrowFlow):
            raise OwnershipError('Loop body must return a BorrowFlow')
        return BorrowFlow(self.paths + result.paths)

    def enter(self, scope):
        return self.apply(lambda path: path.enter(scope))

    def exit(self):
        return self.apply(lambda path: path.exit())

    def declare(self, name):
        return self.apply(lambda path: path.declare(name))

    def borrow(self, owner, reference, mode=None):
        from qrvm.borrow_access import BorrowMode
        selected = BorrowMode.SHARED if mode is None else mode
        return self.apply(lambda path: path.borrow(owner, reference, selected))

    def release(self, reference):
        return self.apply(lambda path: path.release(reference))

    def move(self, source, destination):
        return self.apply(lambda path: path.move(source, destination))

    def drop(self, owner):
        return self.apply(lambda path: path.drop(owner))

    def read(self, name):
        self.check(lambda path: path.read(name))

    def write(self, name):
        self.check(lambda path: path.write(name))
