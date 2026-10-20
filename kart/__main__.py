"""Command-line interface for the initial local-only Kart implementation."""
import argparse
from pathlib import Path
from .core import KartError, read_manifest, write_lock, verify_lock, cache_packages, install_packages, installed_packages, build_preflight, diagnose_project, project_status, update_local
from . import __version__

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kart")
    parser.add_argument("--version", action="version", version=f"Kart {__version__}")
    parser.add_argument("command", choices=("info", "lock", "verify", "cache", "install", "paths", "check", "doctor", "status", "update"))
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "info":
            project = read_manifest(Path(args.project))
            print(f"{project.name} {project.version}")
            for name, path in project.dependencies:
                print(f"  {name}: {path}")
        elif args.command == "lock":
            print(write_lock(Path(args.project)))
        elif args.command == "cache":
            for path in cache_packages(Path(args.project)):
                print(path)
        elif args.command == "install":
            print(install_packages(Path(args.project)))
        elif args.command == "paths":
            for name, path in sorted(installed_packages(Path(args.project)).items()):
                print(f"{name}: {path}")
        elif args.command in ("doctor", "status"):
            # Status is a read-only alias with the same stable diagnostics.
            checks = diagnose_project(Path(args.project))
            for stage, passed, detail in checks:
                print(f"{stage}: {'OK' if passed else 'FAIL'}" + (f" - {detail}" if not passed else ""))
            return 0 if all(passed for _, passed, _ in checks) else 1
        elif args.command == "update":
            print(update_local(Path(args.project)))
        elif args.command == "check":
            packages = build_preflight(Path(args.project))
            print(f"Kart build preflight OK ({len(packages)} dependencies)")
        else:
            verify_lock(Path(args.project))
            print("Kart lockfile verified")
        return 0
    except KartError as error:
        parser.exit(1, f"kart: {error}\n")

if __name__ == "__main__":
    raise SystemExit(main())
