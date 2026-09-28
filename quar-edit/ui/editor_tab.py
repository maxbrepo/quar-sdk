from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from session.working_document import WorkingDocument
from ui.editor_view import EditorView


ModifiedCallback = Callable[["EditorTab"], None]


class EditorTab(Gtk.Box):
    """Represent one editable QEdit document tab."""

    MAX_DYNAMIC_NAME_LENGTH = 50

    def __init__(
        self,
        working_document: WorkingDocument,
    ) -> None:
        """Create an editor tab connected to a persistent document."""

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.working_document = working_document
        self._modified_callback: ModifiedCallback | None = None

        self.set_hexpand(True)
        self.set_vexpand(True)

        self.editor_view = EditorView()
        self.editor_view.set_hexpand(True)
        self.editor_view.set_vexpand(True)

        # Restore the persistent text before enabling change notifications.
        self.editor_view.set_text(
            self.working_document.text
        )

        # EditorTab owns the EditorView callback.
        # External components register with EditorTab instead.
        self.editor_view.set_modified_callback(
            self._on_editor_modified
        )

        self.append(self.editor_view)

        # Cursor restoration can happen immediately, but scroll restoration
        # must wait until GTK has measured the document and its viewport.
        self.editor_view.set_cursor_offset(
            self.working_document.cursor_offset
        )
        GLib.idle_add(
            self._restore_navigation_state
        )

    def set_modified_callback(
        self,
        callback: ModifiedCallback,
    ) -> None:
        """Register a callback for user modifications to this tab."""

        self._modified_callback = callback

    def _on_editor_modified(self) -> None:
        """Synchronize an editor change with the working document."""

        text = self.editor_view.get_text()

        self.working_document.set_text(text)

        if self._modified_callback is not None:
            self._modified_callback(self)

    def get_text(self) -> str:
        """Return the current editor text."""

        return self.editor_view.get_text()

    def set_text(
        self,
        text: str,
        modified: bool = False,
    ) -> None:
        """Replace the editor text and synchronize its working state."""

        self.editor_view.set_text(text)

        self.working_document.text = text
        self.working_document.modified = modified

    def save_checkpoint(self) -> None:
        """Persist text and per-tab navigation without touching the source."""

        self.working_document.text = self.get_text()
        self._capture_navigation_state()
        self.working_document.save_checkpoint()

    def _capture_navigation_state(self) -> None:
        """Copy the current cursor and viewport positions into the document."""

        self.working_document.cursor_offset = (
            self.editor_view.get_cursor_offset()
        )
        self.working_document.vertical_scroll = (
            self.editor_view.get_vertical_scroll_position()
        )
        self.working_document.horizontal_scroll = (
            self.editor_view.get_horizontal_scroll_position()
        )

    def _restore_navigation_state(self) -> bool:
        """Restore this tab's viewport after GTK has completed layout."""

        self.editor_view.set_vertical_scroll_position(
            self.working_document.vertical_scroll
        )
        self.editor_view.set_horizontal_scroll_position(
            self.working_document.horizontal_scroll
        )

        return False

    def get_base_display_name(self) -> str:
        """Return the tab name without a modified-state indicator."""

        if self.working_document.file_path is not None:
            return self.working_document.file_path.name

        dynamic_name = self._get_dynamic_name()

        if dynamic_name:
            return dynamic_name

        return "empty"

    def get_display_name(self) -> str:
        """Return the complete visible tab name."""

        base_name = self.get_base_display_name()

        if self.working_document.modified:
            return f"● {base_name}"

        if self.working_document.file_path is None:
            return f"*{base_name}"

        return base_name

    def _get_dynamic_name(self) -> str:
        """Derive an unsaved tab name from its first meaningful line."""

        for line in self.get_text().splitlines():
            cleaned_line = " ".join(
                line.strip().split()
            )

            if not cleaned_line:
                continue

            return cleaned_line[
                :self.MAX_DYNAMIC_NAME_LENGTH
            ]

        return ""

    def get_editor_view(self) -> EditorView:
        """Return the editable view owned by this tab."""

        return self.editor_view

    def get_working_document(
        self,
    ) -> WorkingDocument:
        """Return the persistent document owned by this tab."""

        return self.working_document