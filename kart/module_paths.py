"""Strict, read-only adapter from Kart installations to module source paths."""
from pathlib import Path
from .core import KartError, installed_packages


def resolve_package_module(project: Path, package: str, module: str) -> Path:
    """Return a verified installed .vq module path; never execute or parse it."""
    packages = installed_packages(project)
    if package not in packages:
        raise KartError(f"Package is not an installed dependency: '{package}'")
    if not isinstance(module, str) or not module or any(
        not segment.isidentifier() or not segment.isascii()
        for segment in module.split('.')
    ):
        raise KartError(f"Invalid package module name: '{module}'")
    base = packages[package]
    candidate = base.joinpath(*module.split('.')).with_suffix('.vq')
    if candidate.is_symlink() or not candidate.is_file():
        raise KartError(f"Package module not found or unsafe: '{package}.{module}'")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base):
        raise KartError(f"Package module escapes installation: '{package}.{module}'")
    return resolved
