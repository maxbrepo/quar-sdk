"""Best-effort atomic file replacement for the QRVM bootstrap.

Writes are staged alongside the destination, flushed and synced, then
installed with os.replace. This does not guarantee durability after power loss
or identical metadata/permissions across replacement.
"""

import os
import stat
import tempfile
from pathlib import Path


def _sync_parent_directory_best_effort(parent: Path) -> bool:
    """Try to persist a rename directory entry on POSIX; return success."""
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if os.name != "posix" or not isinstance(directory_flag, int):
        return False
    descriptor = None
    try:
        descriptor = os.open(parent, os.O_RDONLY | directory_flag)
        os.fsync(descriptor)
        return True
    except OSError:
        # The replacement has already committed. Raising here would falsely
        # imply that the previous file is still present.
        return False
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def write_bytes_atomic(destination: Path, content: bytes) -> None:
    """Replace a file only after staging all bytes; return None on success."""
    if not isinstance(content, bytes):
        raise TypeError("Atomic binary writes require bytes")

    # Preserve the existing file's permission bits, not its identity or owner.
    # A symlink is rejected rather than silently replacing the link itself.
    if destination.is_symlink():
        raise OSError("Atomic replacement of symbolic links is unsupported")
    existing_mode = None
    try:
        existing_mode = stat.S_IMODE(destination.stat().st_mode)
    except FileNotFoundError:
        pass

    temporary_path = None
    try:
        descriptor, filename = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".vqtmp", dir=destination.parent
        )
        temporary_path = Path(filename)
        with os.fdopen(descriptor, "wb") as stream:
            if existing_mode is not None:
                os.chmod(temporary_path, existing_mode)
            written = stream.write(content)
            if written != len(content):
                raise OSError("Incomplete atomic write")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
        _sync_parent_directory_best_effort(destination.parent)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                # Do not mask the original failure. A failed cleanup may
                # require manual removal of the temporary file.
                pass


def write_text_atomic(destination: Path, content: str) -> None:
    """Encode UTF-8 and replace a file atomically; return None on success."""
    if not isinstance(content, str):
        raise TypeError("Atomic text writes require string")
    write_bytes_atomic(destination, content.encode("utf-8"))
