"""Conservative may-alias facts for tracked reference-like variables.

This is a standalone static-analysis prototype, not a claim that Quar has
reference assignment semantics. Frontend type rules must determine which
assignments establish aliases before this model is used by production passes.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AliasState:
    """Possible shared locations; unknown targets conservatively alias everyone."""
    targets: Mapping[str, frozenset[str]]
    unknown: frozenset[str] = frozenset()

    def __post_init__(self):
        normalized = {name: frozenset(values) for name, values in self.targets.items()}
        if not all(isinstance(name, str) and name and values for name, values in normalized.items()):
            raise ValueError('Each tracked variable requires nonempty possible targets')
        if not self.unknown <= normalized.keys():
            raise ValueError('Unknown aliases must be tracked variables')
        object.__setattr__(self, 'targets', normalized)
        object.__setattr__(self, 'unknown', frozenset(self.unknown))

    @classmethod
    def independent(cls, names):
        names = frozenset(names)
        return cls({name: frozenset({name}) for name in names})

    def copy_alias(self, destination, source):
        """Model reference rebinding, not a value copy."""
        self._require(destination, source)
        targets = dict(self.targets)
        targets[destination] = targets[source]
        unknown = (self.unknown - {destination}) | ({destination} if source in self.unknown else set())
        return AliasState(targets, frozenset(unknown))

    def fresh(self, name, location):
        """Rebind a name to a proven fresh location."""
        self._require(name)
        if not isinstance(location, str) or not location:
            raise ValueError('Fresh location must have a nonempty identifier')
        targets = dict(self.targets)
        targets[name] = frozenset({location})
        return AliasState(targets, self.unknown - {name})

    def escape(self, name):
        """An unknown external reference may refer to any tracked location."""
        self._require(name)
        return AliasState(self.targets, self.unknown | {name})

    def may_alias(self, left, right):
        self._require(left, right)
        return (left in self.unknown or right in self.unknown
                or bool(self.targets[left] & self.targets[right]))

    def affected(self, modified):
        """All tracked names potentially affected by writes through modified names."""
        modified = frozenset(modified)
        self._require(*modified)
        return frozenset(name for name in self.targets
                         if any(self.may_alias(name, other) for other in modified))

    def join(self, other):
        """Union possibilities from two control-flow paths (may analysis)."""
        if self.targets.keys() != other.targets.keys():
            raise ValueError('Cannot join different tracked variable sets')
        return AliasState({name: self.targets[name] | other.targets[name]
                           for name in self.targets}, self.unknown | other.unknown)

    def _require(self, *names):
        missing = set(names) - self.targets.keys()
        if missing:
            raise KeyError(f'Untracked alias names: {sorted(missing)}')
