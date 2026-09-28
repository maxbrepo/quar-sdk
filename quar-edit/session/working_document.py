from __future__ import annotations

import json
import uuid

from pathlib import Path


class WorkingDocument:
    """Represent a persistent QEdit working document.

    A WorkingDocument stores the editor's current working state separately
    from the original user file.

    Saving a checkpoint never modifies the original source file.
    """

    def __init__(
        self,
        state_directory: Path,
        session_id: str | None = None,
    ) -> None:
        """Create a new working document or reference an existing one."""

        self.state_directory = state_directory
        self.session_id = session_id or str(uuid.uuid4())

        self.file_path: Path | None = None
        self.text: str = ""
        self.modified: bool = False

        # Persistent per-tab editor navigation state.
        self.cursor_offset: int = 0
        self.vertical_scroll: float = 0.0
        self.horizontal_scroll: float = 0.0

    @property
    def documents_directory(self) -> Path:
        """Return the directory containing persistent working documents."""

        return self.state_directory / "documents"

    @property
    def metadata_path(self) -> Path:
        """Return the metadata file path for this working document."""

        return self.documents_directory / f"{self.session_id}.json"

    @property
    def content_path(self) -> Path:
        """Return the checkpoint content path for this working document."""

        return self.documents_directory / f"{self.session_id}.txt"

    def set_text(self, text: str) -> None:
        """Update the working text and mark the document as modified."""

        self.text = text
        self.modified = True

    def set_file_path(self, file_path: Path | None) -> None:
        """Associate the working document with an original file."""

        self.file_path = file_path

    def mark_clean(self) -> None:
        """Mark the working document as synchronized with its source file."""

        self.modified = False

    def save_checkpoint(self) -> None:
        """Persist the current working state without touching the source file."""

        self.documents_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata = {
            "session_id": self.session_id,
            "file_path": (
                str(self.file_path)
                if self.file_path is not None
                else None
            ),
            "modified": self.modified,
            "cursor_offset": self.cursor_offset,
            "vertical_scroll": self.vertical_scroll,
            "horizontal_scroll": self.horizontal_scroll,
        }

        # Write the text checkpoint separately from its metadata.
        self.content_path.write_text(
            self.text,
            encoding="utf-8",
        )

        self.metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load_checkpoint(self) -> None:
        """Restore this working document from its persistent checkpoint."""

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Checkpoint metadata not found: {self.metadata_path}"
            )

        if not self.content_path.exists():
            raise FileNotFoundError(
                f"Checkpoint content not found: {self.content_path}"
            )

        metadata = json.loads(
            self.metadata_path.read_text(
                encoding="utf-8",
            )
        )

        stored_session_id = metadata.get("session_id")

        if stored_session_id != self.session_id:
            raise ValueError(
                "Checkpoint session ID does not match "
                "the requested working document."
            )

        stored_file_path = metadata.get("file_path")

        self.file_path = (
            Path(stored_file_path)
            if stored_file_path is not None
            else None
        )

        self.modified = bool(
            metadata.get("modified", False)
        )

        self.text = self.content_path.read_text(
            encoding="utf-8",
        )