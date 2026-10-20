"""Local-only project manifests and deterministic dependency locks for Kart."""
from __future__ import annotations

import hashlib
import json
import re
import os
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$")


class KartError(Exception):
    """A manifest or dependency resolution error."""


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    root: Path
    dependencies: tuple[tuple[str, Path], ...]
    constraints: tuple[tuple[str, str], ...] = ()


def version_key(value: str) -> tuple[int, int, int]:
    """Return numeric components of a validated version."""
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise KartError(f"Invalid version '{value}'")
    major, minor, patch = value.split("-", 1)[0].split(".")
    return int(major), int(minor), int(patch)


def validate_constraint(value: str) -> None:
    """Validate a minimal conjunction of numeric version comparisons."""
    if not isinstance(value, str) or not value.strip():
        raise KartError("Version constraint must be a nonempty string")
    if value == "*":
        return
    for term in value.split(","):
        match = re.fullmatch(r"\s*(>=|<=|==|>|<)?\s*(\d+\.\d+\.\d+)\s*", term)
        if match is None:
            raise KartError(f"Invalid or unsupported version constraint '{value}'")


def matches_version(version: str, constraint: str) -> bool:
    """Compare numeric release components against all constraint terms."""
    validate_constraint(constraint)
    if constraint == "*":
        return True
    if "-" in version:
        raise KartError("Prerelease version comparisons are not supported yet")
    current = version_key(version)
    operations = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        "==": lambda a, b: a == b,
    }
    for term in constraint.split(","):
        match = re.fullmatch(r"\s*(>=|<=|==|>|<)?\s*(\d+\.\d+\.\d+)\s*", term)
        assert match is not None
        operator, expected = match.groups()
        if not operations[operator or "=="](current, version_key(expected)):
            return False
    return True


def read_manifest(folder: Path) -> Package:
    root = folder.resolve()
    manifest = root / "kart.toml"
    try:
        content = manifest.read_bytes()
        data = tomllib.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise KartError(f"Cannot read manifest '{manifest}': {exc}") from exc
    project = data.get("package")
    if not isinstance(project, dict):
        raise KartError(f"Missing [package] in '{manifest}'")
    name, version = project.get("name"), project.get("version")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise KartError(f"Invalid package name in '{manifest}'")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise KartError(f"Invalid package version in '{manifest}'")
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise KartError(f"[dependencies] must be a table in '{manifest}'")
    parsed = []
    constraints = []
    for dep_name, value in sorted(dependencies.items()):
        if not NAME.fullmatch(dep_name):
            raise KartError(f"Invalid dependency name: {dep_name}")
        if not isinstance(value, dict) or "path" not in value or set(value) - {"path", "version"}:
            raise KartError(f"Dependency '{dep_name}' requires a local path and optional version")
        constraint = value.get("version", "*")
        validate_constraint(constraint)
        path = value["path"]
        if not isinstance(path, str) or not path.strip():
            raise KartError(f"Invalid path for dependency '{dep_name}'")
        target = (root / path).resolve()
        if not target.is_dir():
            raise KartError(f"Dependency '{dep_name}' not found: {target}")
        parsed.append((dep_name, target))
        constraints.append((dep_name, constraint))
    return Package(name, version, root, tuple(parsed), tuple(constraints))


def resolve(folder: Path) -> dict:
    """Resolve local packages; reject cycles and conflicting package identities."""
    packages: dict[str, Package] = {}
    visiting: set[Path] = set()
    visited: set[Path] = set()
    canonical: dict[Path, Package] = {}
    requests: dict[str, list[tuple[str, str, str]]] = {}

    def visit(path: Path) -> Package:
        path = path.resolve()
        if path in visiting:
            raise KartError(f"Circular dependency at '{path}'")
        if path in visited:
            return canonical[path]
        visiting.add(path)
        package = read_manifest(path)
        previous = packages.get(package.name)
        if previous and (previous.version, previous.root) != (package.version, package.root):
            raise KartError(f"Conflicting dependency: '{package.name}'")
        packages[package.name] = package
        canonical[path] = package
        for declared_name, target in package.dependencies:
            child = visit(target)
            constraint = dict(package.constraints)[declared_name]
            requests.setdefault(child.name, []).append((package.name, constraint, str(target)))
            if not matches_version(child.version, constraint):
                all_requests = "; ".join(
                    f"{parent} requires {required}" for parent, required, _ in requests[child.name]
                )
                raise KartError(
                    f"Version conflict for '{declared_name}': version {child.version} "
                    f"does not satisfy requirements: {all_requests}"
                )
            if child.name != declared_name:
                raise KartError(
                    f"Dependency '{declared_name}' declares package name '{child.name}'"
                )
        visiting.remove(path)
        visited.add(path)
        return package

    root = visit(folder)
    entries = []
    for package in sorted(packages.values(), key=lambda item: (item.name, item.version)):
        manifest_bytes = (package.root / "kart.toml").read_bytes()
        entries.append({
            "name": package.name,
            "version": package.version,
            "source": "local",
            "path": os.path.relpath(package.root, folder.resolve()).replace(os.sep, "/"),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "dependencies": [name for name, _ in package.dependencies],
        })
    return {"lock_version": 1, "root": root.name, "packages": entries}


def write_lock(folder: Path) -> Path:
    root = folder.resolve()
    payload = resolve(root)
    destination = root / "kart.lock"
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


def verify_lock(folder: Path) -> dict:
    """Verify the existing lockfile against current local manifests without modifying it."""
    root = folder.resolve()
    lockfile = root / "kart.lock"
    try:
        locked = json.loads(lockfile.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KartError(f"Missing lockfile '{lockfile}'; run 'kart lock' first") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KartError(f"Cannot read lockfile '{lockfile}': {exc}") from exc
    if not isinstance(locked, dict) or locked.get("lock_version") != 1:
        raise KartError(f"Unsupported or malformed lockfile '{lockfile}'")
    expected = resolve(root)
    if locked != expected:
        raise KartError(
            f"Lockfile '{lockfile}' is outdated or inconsistent with local manifests; "
            "run 'kart lock' to regenerate it"
        )
    return expected


# Kart's initial package store is local-only. Never execute package code.
_SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", ".kart", "build", "dist"}
_SKIP_FILES = {"kart.lock", ".DS_Store"}


def _package_files(root: Path) -> list[tuple[Path, Path]]:
    """Return safe, sorted relative paths and source files for a local package."""
    result: list[tuple[Path, Path]] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for directory in list(directories):
            path = current_path / directory
            if path.is_symlink():
                raise KartError(f"Symbolic links are not supported in packages: '{path}'")
            if directory in _SKIP_DIRS:
                directories.remove(directory)
        for filename in filenames:
            path = current_path / filename
            if filename in _SKIP_FILES or filename.endswith((".pyc", ".pyo")):
                continue
            if path.is_symlink() or not path.is_file():
                raise KartError(f"Unsupported package entry: '{path}'")
            result.append((path.relative_to(root), path))
    return sorted(result, key=lambda item: item[0].as_posix())


def package_digest(root: Path) -> str:
    """Hash relative filenames and file contents, not absolute source paths."""
    digest = hashlib.sha256()
    for relative, source in _package_files(root):
        name = relative.as_posix().encode("utf-8")
        data = source.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def cache_packages(folder: Path, store: Path | None = None) -> list[Path]:
    """Cache immutable local package snapshots under a content-addressed store.

    Existing snapshots are verified, never overwritten. This is not an installer.
    """
    root = folder.resolve()
    resolve(root)  # Validate the entire dependency graph before any write.
    if store is None:
        store = Path.home() / ".cache" / "kart" / "packages"
    store = store.expanduser().resolve()
    packages: dict[str, Package] = {}
    visited: set[Path] = set()

    def collect(path: Path) -> None:
        path = path.resolve()
        if path in visited:
            return
        visited.add(path)
        package = read_manifest(path)
        packages[package.name] = package
        for _, child in package.dependencies:
            collect(child)

    collect(root)
    results = []
    for package in sorted(packages.values(), key=lambda item: item.name):
        digest = package_digest(package.root)
        target = store / f"{package.name}-{package.version}-{digest}"
        if target.exists() or target.is_symlink():
            if not target.is_dir() or target.is_symlink() or package_digest(target) != digest:
                raise KartError(f"Corrupted or unsafe cache entry '{target}'")
            results.append(target)
            continue
        store.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".kart-stage-", dir=store))
        try:
            for relative, source in _package_files(package.root):
                destination = temporary / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination, follow_symlinks=False)
            if package_digest(temporary) != digest:
                raise KartError(f"Package changed while copying: '{package.name}'")
            if target.exists() or target.is_symlink():
                raise KartError(f"Cache entry appeared during write: '{target}'")
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        results.append(target)
    return results


def install_packages(folder: Path, store: Path | None = None) -> Path:
    """Install local dependencies into a project-private snapshot directory.

    The installation is a copy of verified cached content, not a module-loader
    integration. Existing installations are replaced only after staging succeeds.
    Returns the project-local index path.
    """
    root = folder.resolve()
    install_root = root / ".kart"
    if install_root.is_symlink():
        raise KartError(f"Unsafe installation directory '{install_root}'")
    graph = resolve(root)
    cached = cache_packages(root, store)
    cache_by_name = {}
    for entry in graph["packages"]:
        candidates = [path for path in cached if path.name.startswith(
            f"{entry['name']}-{entry['version']}-"
        )]
        if len(candidates) != 1:
            raise KartError(f"Missing cached package '{entry['name']}'")
        cache_by_name[entry["name"]] = candidates[0]
    install_root.mkdir(parents=True, exist_ok=True)
    packages_dir = install_root / "packages"
    index_path = install_root / "installed.json"
    if packages_dir.is_symlink() or index_path.is_symlink():
        raise KartError("Unsafe existing installation path")

    stage = Path(tempfile.mkdtemp(prefix=".install-stage-", dir=install_root))
    try:
        staged_packages = stage / "packages"
        staged_packages.mkdir()
        index = {"format_version": 1, "root": graph["root"], "packages": []}
        for entry in graph["packages"]:
            if entry["name"] == graph["root"]:
                continue
            source = cache_by_name[entry["name"]]
            destination = staged_packages / entry["name"]
            shutil.copytree(source, destination, symlinks=False)
            if package_digest(destination) != package_digest(source):
                raise KartError(f"Installed package differs from cache: '{entry['name']}'")
            index["packages"].append({
                "name": entry["name"],
                "version": entry["version"],
                "digest": package_digest(destination),
                "path": f".kart/packages/{entry['name']}",
            })
        (stage / "installed.json").write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        # Keep the previous installation untouched if a stage operation fails.
        # Replacement uses a temporary backup and restores it on failure.
        backup = install_root / ".install-backup"
        if backup.exists() or backup.is_symlink():
            raise KartError(f"Stale installation backup '{backup}'")
        backup.mkdir()
        moved_old = []
        moved_new = []
        try:
            for target in (packages_dir, index_path):
                if target.exists():
                    target.rename(backup / target.name)
                    moved_old.append(target)
            for name in ("packages", "installed.json"):
                (stage / name).rename(install_root / name)
                moved_new.append(install_root / name)
        except OSError as install_error:
            try:
                for target in reversed(moved_new):
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                for target in reversed(moved_old):
                    (backup / target.name).rename(target)
            except OSError as rollback_error:
                # Preserve the backup for manual recovery if rollback fails.
                raise KartError(
                    f"Installation failed ({install_error}); rollback failed "
                    f"({rollback_error}); inspect '{backup}'"
                ) from install_error
            else:
                shutil.rmtree(backup)
            raise
        else:
            shutil.rmtree(backup)
    except OSError as exc:
        raise KartError(f"Cannot install local packages: {exc}") from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return index_path


def installed_packages(folder: Path, *, require_lock: bool = True) -> dict[str, Path]:
    """Validate the installed index and return canonical package source directories.

    The mapping is intended for a module loader; it does not execute code.
    """
    root = folder.resolve()
    if require_lock:
        verify_lock(root)
    index_file = root / ".kart" / "installed.json"
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KartError(f"Cannot read installed package index '{index_file}': {exc}") from exc
    if not isinstance(index, dict) or index.get("format_version") != 1:
        raise KartError("Unsupported installed package index")
    if index.get("root") != read_manifest(root).name or not isinstance(index.get("packages"), list):
        raise KartError("Installed package index does not match project")
    expected = {item["name"]: item for item in resolve(root)["packages"] if item["name"] != index["root"]}
    result: dict[str, Path] = {}
    for item in index["packages"]:
        if not isinstance(item, dict):
            raise KartError("Malformed installed package entry")
        name = item.get("name")
        if not isinstance(name, str) or name not in expected or name in result:
            raise KartError("Unexpected or duplicate installed package")
        expected_path = root / ".kart" / "packages" / name
        if item.get("path") != f".kart/packages/{name}" or expected_path.is_symlink():
            raise KartError(f"Unsafe installed package path for '{name}'")
        if item.get("version") != expected[name]["version"]:
            raise KartError(f"Installed version mismatch for '{name}'")
        if not isinstance(item.get("digest"), str) or package_digest(expected_path) != item["digest"]:
            raise KartError(f"Installed content mismatch for '{name}'")
        result[name] = expected_path.resolve()
    if set(result) != set(expected):
        raise KartError("Installed packages are missing or outdated")
    packages_dir = root / ".kart" / "packages"
    if packages_dir.is_symlink() or not packages_dir.is_dir():
        raise KartError("Unsafe or missing installed packages directory")
    actual = {entry.name for entry in packages_dir.iterdir()}
    if actual != set(expected):
        raise KartError("Unexpected or missing directories in installed packages")
    if any(not entry.is_dir() or entry.is_symlink() for entry in packages_dir.iterdir()):
        raise KartError("Unsafe installed package directory")
    return result


def build_preflight(folder: Path) -> dict[str, str]:
    """Validate lock and installed snapshots before build; does not invoke compiler."""
    return {name: str(path) for name, path in installed_packages(folder).items()}


def diagnose_project(folder: Path) -> tuple[tuple[str, bool, str], ...]:
    """Check Kart project stages independently without changing project files.

    Returns ordered (stage, success, explanation) records.
    """
    root = folder.resolve()
    checks = (
        ("manifest", lambda: read_manifest(root)),
        ("resolution", lambda: resolve(root)),
        ("lockfile", lambda: verify_lock(root)),
        ("installation", lambda: installed_packages(root)),
    )
    results = []
    for label, operation in checks:
        try:
            operation()
        except (KartError, OSError, ValueError) as exc:
            results.append((label, False, str(exc)))
        else:
            results.append((label, True, "OK"))
    return tuple(results)


def project_status(folder: Path) -> tuple[tuple[str, bool, str], ...]:
    """Return read-only diagnostics for a local project; never repair implicitly."""
    return diagnose_project(folder)


def update_local(folder: Path, store: Path | None = None) -> Path:
    """Refresh a local project's lock and installed snapshots.

    Restore the previous lockfile if installation fails. The installer itself
    preserves the previous package index when staging fails.
    """
    root = folder.resolve()
    lockfile = root / "kart.lock"
    install_root = root / ".kart"
    if install_root.is_symlink() or (install_root / ".install-backup").exists():
        raise KartError("Unsafe or incomplete prior installation; inspect .kart before updating")
    if lockfile.is_symlink():
        raise KartError(f"Unsafe lockfile '{lockfile}'")
    previous = lockfile.read_bytes() if lockfile.exists() else None
    # Resolve and hash before changing any on-disk project state.
    resolve(root)
    try:
        write_lock(root)
        return install_packages(root, store)
    except (KartError, OSError) as exc:
        try:
            if previous is None:
                lockfile.unlink(missing_ok=True)
            else:
                lockfile.write_bytes(previous)
        except OSError as rollback_error:
            raise KartError(f"Update failed ({exc}); lockfile rollback failed: {rollback_error}") from exc
        if isinstance(exc, OSError):
            raise KartError(f"Cannot update local packages: {exc}") from exc
        raise
