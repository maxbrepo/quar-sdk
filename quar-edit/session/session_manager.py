from __future__ import annotations

import json

from pathlib import Path

from session.working_document import WorkingDocument


class SessionManager:
    """Manage the persistent QEdit editing session.

    The session stores which working documents are open, their order,
    and which document is currently active.
    """

    def __init__(self, state_directory: Path) -> None:
        """Create a session manager for the specified state directory."""

        self.state_directory = state_directory

        self.documents: list[WorkingDocument] = []
        self.active_session_id: str | None = None

    @property
    def session_path(self) -> Path:
        """Return the path of the persistent session metadata file."""

        return self.state_directory / "session.json"

    def create_document(self) -> WorkingDocument:
        """Create and register a new persistent working document."""

        document = WorkingDocument(
            self.state_directory
        )

        self.documents.append(document)
        self.active_session_id = document.session_id

        # Create the first checkpoint immediately.
        # This allows even an untouched empty tab to survive a restart.
        document.save_checkpoint()

        self.save_session()

        return document

    def add_document(
        self,
        document: WorkingDocument,
    ) -> None:
        """Register an existing working document in the session."""

        for existing_document in self.documents:
            if existing_document.session_id == document.session_id:
                return

        self.documents.append(document)
        self.active_session_id = document.session_id

        self.save_session()

    def remove_document(
        self,
        session_id: str,
    ) -> bool:
        """Remove a working document from the active session.

        This removes the document from session.json but deliberately does
        not delete its checkpoint yet. Checkpoint deletion will be handled
        separately once QEdit's close/discard policy is implemented.
        """

        original_count = len(self.documents)

        self.documents = [
            document
            for document in self.documents
            if document.session_id != session_id
        ]

        if len(self.documents) == original_count:
            return False

        if self.active_session_id == session_id:
            if self.documents:
                self.active_session_id = (
                    self.documents[-1].session_id
                )
            else:
                self.active_session_id = None

        self.save_session()

        return True

    def delete_checkpoint(
        self,
        document: WorkingDocument,
    ) -> None:
        """Delete the persistent checkpoint of a deliberately closed document."""

        if document.metadata_path.exists():
            document.metadata_path.unlink()

        if document.content_path.exists():
            document.content_path.unlink()

    def set_active_document(
        self,
        session_id: str,
    ) -> bool:
        """Set the active working document."""

        for document in self.documents:
            if document.session_id == session_id:
                self.active_session_id = session_id
                self.save_session()
                return True

        return False

    def get_active_document(
        self,
    ) -> WorkingDocument | None:
        """Return the currently active working document."""

        if self.active_session_id is None:
            return None

        for document in self.documents:
            if document.session_id == self.active_session_id:
                return document

        return None

    def save_session(self) -> None:
        """Persist the current QEdit session metadata."""

        self.state_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        session_data = {
            "documents": [
                document.session_id
                for document in self.documents
            ],
            "active_session_id": self.active_session_id,
        }

        self.session_path.write_text(
            json.dumps(
                session_data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load_session(self) -> None:
        """Restore all working documents from the persistent session."""

        self.documents = []
        self.active_session_id = None

        if not self.session_path.exists():
            return

        session_data = json.loads(
            self.session_path.read_text(
                encoding="utf-8",
            )
        )

        stored_documents = session_data.get(
            "documents",
            []
        )

        for session_id in stored_documents:
            document = WorkingDocument(
                self.state_directory,
                session_id,
            )

            try:
                document.load_checkpoint()
            except (
                FileNotFoundError,
                ValueError,
                json.JSONDecodeError,
            ):
                # A damaged or incomplete checkpoint must not prevent
                # the rest of the QEdit session from being restored.
                continue

            self.documents.append(document)

        requested_active_id = session_data.get(
            "active_session_id"
        )

        if any(
            document.session_id == requested_active_id
            for document in self.documents
        ):
            self.active_session_id = requested_active_id

        elif self.documents:
            self.active_session_id = (
                self.documents[0].session_id
            )

    def checkpoint_all(self) -> None:
        """Persist every working document and the session metadata."""

        for document in self.documents:
            document.save_checkpoint()

        self.save_session()