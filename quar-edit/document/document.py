from pathlib import Path


class Document:
    """Represent the document currently loaded in QEdit."""

    def __init__(self) -> None:
        self.file_path: Path | None = None
        self.modified: bool = False

    def new(self) -> None:
        """Reset the document to a new clean unsaved file."""
        self.file_path = None
        self.modified = False

    def load(self, file_path: Path) -> str:
        """Load a UTF-8 text file and return its contents."""
        text = file_path.read_text(
            encoding="utf-8"
        )

        self.file_path = file_path
        self.modified = False

        return text

    def save(self, text: str) -> None:
        """Save text to the current document path."""
        if self.file_path is None:
            raise ValueError(
                "Document has no file path."
            )

        self.file_path.write_text(
            text,
            encoding="utf-8",
        )

        self.modified = False

    def save_as(
        self,
        file_path: Path,
        text: str,
    ) -> None:
        """Save text to a new path and make it the current document."""
        file_path.write_text(
            text,
            encoding="utf-8",
        )

        self.file_path = file_path
        self.modified = False

    def mark_modified(self) -> None:
        """Mark the document as containing unsaved changes."""
        self.modified = True

    def mark_clean(self) -> None:
        """Mark the document as having no unsaved changes."""
        self.modified = False

    def is_modified(self) -> bool:
        """Return True when the document contains unsaved changes."""
        return self.modified

    def has_file_path(self) -> bool:
        """Return True when the document has a file path."""
        return self.file_path is not None

    def get_display_name(self) -> str:
        """Return the current file name or Untitled."""
        if self.file_path is None:
            return "Untitled"

        return self.file_path.name