from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from session.session_manager import SessionManager
from session.working_document import WorkingDocument
from ui.editor_tab import EditorTab


CloseRequestCallback = Callable[[EditorTab], None]


class TabManager(Gtk.Box):
    """Manage QEdit tabs and their persistent working documents."""

    CHECKPOINT_DELAY_MS = 1000

    def __init__(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Create the tab manager."""

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.session_manager = session_manager
        self.close_request_callback: CloseRequestCallback | None = None

        self.tabs: dict[str, EditorTab] = {}
        self.checkpoint_timers: dict[str, int] = {}

        self.set_hexpand(True)
        self.set_vexpand(True)

        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        self.notebook.set_scrollable(True)

        self.notebook.connect(
            "switch-page",
            self._on_switch_page,
        )

        self.append(self.notebook)

    def set_close_request_callback(
        self,
        callback: CloseRequestCallback,
    ) -> None:
        """Register the function responsible for close requests."""

        self.close_request_callback = callback

    def create_tab(self) -> EditorTab:
        """Create a new persistent empty editor tab."""

        document = self.session_manager.create_document()

        return self._add_editor_tab(
            document,
            make_active=True,
        )

    def restore_tabs(self) -> None:
        """Restore tabs from the persistent QEdit session."""

        self.session_manager.load_session()

        for document in self.session_manager.documents:
            self._add_editor_tab(
                document,
                make_active=False,
            )

        active_document = self.session_manager.get_active_document()

        if active_document is not None:
            self.select_tab(active_document.session_id)

    def _add_editor_tab(
        self,
        document: WorkingDocument,
        make_active: bool,
    ) -> EditorTab:
        """Create the GTK editor page for a working document."""

        editor_tab = EditorTab(document)
        self.tabs[document.session_id] = editor_tab

        tab_header = self._create_tab_header(editor_tab)

        self.notebook.append_page(
            editor_tab,
            tab_header,
        )

        editor_tab.set_modified_callback(
            self._on_tab_modified
        )

        if make_active:
            self.select_tab(document.session_id)

        return editor_tab

    def _create_tab_header(
        self,
        editor_tab: EditorTab,
    ) -> Gtk.Box:
        """Create a tab header containing its name and close button."""

        tab_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
        )
        tab_header.add_css_class("qedit-tab-header")

        label = Gtk.Label(
            label=editor_tab.get_display_name()
        )
        label.set_width_chars(10)
        label.set_max_width_chars(50)
        label.set_ellipsize(3)
        label.add_css_class("qedit-tab-label")

        close_button = Gtk.Button(label="×")
        close_button.set_has_frame(False)
        close_button.set_focusable(False)
        close_button.add_css_class("qedit-tab-close")
        close_button.set_tooltip_text("Close")

        close_button.connect(
            "clicked",
            self._on_tab_close_clicked,
            editor_tab,
        )

        tab_header.append(label)
        tab_header.append(close_button)

        return tab_header

    def _on_tab_close_clicked(
        self,
        button: Gtk.Button,
        editor_tab: EditorTab,
    ) -> None:
        """Forward a tab close request to the main window."""

        if self.close_request_callback is not None:
            self.close_request_callback(editor_tab)
            return

        if not editor_tab.working_document.modified:
            self.close_tab(editor_tab)

    def close_tab(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Permanently close a tab and remove its checkpoint."""

        document = editor_tab.working_document
        session_id = document.session_id

        timer_id = self.checkpoint_timers.pop(
            session_id,
            None,
        )

        if timer_id is not None:
            GLib.source_remove(timer_id)

        page_number = self.notebook.page_num(editor_tab)

        if page_number >= 0:
            self.notebook.remove_page(page_number)

        self.tabs.pop(session_id, None)

        self.session_manager.remove_document(
            session_id
        )
        self.session_manager.delete_checkpoint(
            document
        )

        if self.get_tab_count() == 0:
            self.create_tab()

    def _on_tab_modified(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """React to a real user edit inside one tab."""

        session_id = editor_tab.working_document.session_id

        self._update_tab_label(editor_tab)
        self._schedule_checkpoint(session_id)

    def _schedule_checkpoint(
        self,
        session_id: str,
    ) -> None:
        """Schedule a delayed persistent checkpoint."""

        previous_timer = self.checkpoint_timers.get(
            session_id
        )

        if previous_timer is not None:
            GLib.source_remove(previous_timer)

        timer_id = GLib.timeout_add(
            self.CHECKPOINT_DELAY_MS,
            self._checkpoint_tab,
            session_id,
        )

        self.checkpoint_timers[session_id] = timer_id

    def _checkpoint_tab(
        self,
        session_id: str,
    ) -> bool:
        """Persist a tab after the debounce interval."""

        self.checkpoint_timers.pop(
            session_id,
            None,
        )

        editor_tab = self.tabs.get(session_id)

        if editor_tab is None:
            return False

        editor_tab.save_checkpoint()
        self.session_manager.save_session()

        return False

    def _update_tab_label(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Update the document name inside a tab header."""

        tab_header = self.notebook.get_tab_label(
            editor_tab
        )

        if not isinstance(tab_header, Gtk.Box):
            return

        child = tab_header.get_first_child()

        if isinstance(child, Gtk.Label):
            child.set_text(
                editor_tab.get_display_name()
            )

    def refresh_tab_label(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Publicly request a refresh of one tab label."""

        self._update_tab_label(editor_tab)

    def _on_switch_page(
        self,
        notebook: Gtk.Notebook,
        page: Gtk.Widget,
        page_number: int,
    ) -> None:
        """Synchronize the selected page with the persistent session."""

        if not isinstance(page, EditorTab):
            return

        session_id = page.working_document.session_id

        self.session_manager.set_active_document(
            session_id
        )

        page.get_editor_view().get_text_view().grab_focus()

    def select_tab(
        self,
        session_id: str,
    ) -> bool:
        """Select a tab using its persistent session identifier."""

        editor_tab = self.tabs.get(session_id)

        if editor_tab is None:
            return False

        page_number = self.notebook.page_num(
            editor_tab
        )

        if page_number < 0:
            return False

        self.notebook.set_current_page(
            page_number
        )

        self.session_manager.set_active_document(
            session_id
        )

        editor_tab.get_editor_view().get_text_view().grab_focus()

        return True

    def get_active_tab(self) -> EditorTab | None:
        """Return the currently selected editable tab."""

        page_number = self.notebook.get_current_page()

        if page_number < 0:
            return None

        page = self.notebook.get_nth_page(
            page_number
        )

        if isinstance(page, EditorTab):
            return page

        return None

    def get_tab_count(self) -> int:
        """Return the number of open tabs."""

        return self.notebook.get_n_pages()

    def checkpoint_all(self) -> None:
        """Immediately persist all open working documents."""

        for editor_tab in self.tabs.values():
            editor_tab.save_checkpoint()

        self.session_manager.save_session()
