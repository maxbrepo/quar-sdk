from __future__ import annotations

import gi

from pathlib import Path

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

from lang.language_manager import get_string, language_manager
from session.session_manager import SessionManager
from ui.editor_tab import EditorTab
from ui.menu_bar import EditorMenuBar
from ui.tab_manager import TabManager
from build.build_manager import BuildManager, BuildResult
from build.build_profiles import PROFILES, get_operation, profile_for_path


class QuarEditWindow(Gtk.ApplicationWindow):
    """Main QEdit application window."""

    def close_current_tab(self) -> None:
        """Request closure of the currently active document tab."""

        editor_tab = self.tab_manager.get_active_tab()

        if editor_tab is None:
            return

        self.request_close_tab(
            editor_tab
        )

    def request_close_tab(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Close a clean tab or ask what to do with unsaved changes."""

        if not editor_tab.working_document.modified:
            self.tab_manager.close_tab(
                editor_tab
            )
            return

        dialog = Gtk.AlertDialog()

        dialog.set_message(
            get_string("dialog.unsaved.title")
        )

        dialog.set_detail(
            get_string("dialog.unsaved.message")
        )

        dialog.set_buttons(
            [
                get_string("dialog.cancel"),
                get_string("dialog.discard"),
                get_string("dialog.save"),
            ]
        )

        dialog.set_cancel_button(0)
        dialog.set_default_button(2)

        dialog.choose(
            self,
            None,
            self._on_close_tab_response,
            editor_tab,
        )

    def _on_close_tab_response(
        self,
        dialog: Gtk.AlertDialog,
        result: Gio.AsyncResult,
        editor_tab: EditorTab,
    ) -> None:
        """Handle the Save, Discard or Cancel decision for a closing tab."""

        try:
            response = dialog.choose_finish(
                result
            )

            # Cancel.
            if response == 0:
                return

            # Discard.
            if response == 1:
                self.tab_manager.close_tab(
                    editor_tab
                )
                return

            # Save.
            if response == 2:
                self._save_tab_before_close(
                    editor_tab
                )

        except Exception as error:
            print(
                f"Close tab dialog error: {error}"
            )

    def _save_tab_before_close(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Save a modified tab before closing it."""

        document = editor_tab.working_document

        if document.file_path is None:
            self._save_as_before_close(
                editor_tab
            )
            return

        try:
            text = editor_tab.get_text()

            document.file_path.write_text(
                text,
                encoding="utf-8",
            )

            document.text = text
            document.mark_clean()

            self.tab_manager.close_tab(
                editor_tab
            )

        except Exception as error:
            print(
                f"Save before close error: {error}"
            )

    def _save_as_before_close(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Request a filename before closing an unnamed modified tab."""

        dialog = Gtk.FileDialog()

        suggested_name = (
            editor_tab.get_base_display_name()
        )

        if suggested_name != "empty":
            dialog.set_initial_name(
                suggested_name
            )

        dialog.save(
            self,
            None,
            self._on_save_as_before_close_finished,
            editor_tab,
        )

    def _on_save_as_before_close_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
        editor_tab: EditorTab,
    ) -> None:
        """Save an unnamed tab and close it after a successful save."""

        try:
            file = dialog.save_finish(
                result
            )

            if file is None:
                return

            file_path_string = file.get_path()

            if file_path_string is None:
                return

            file_path = Path(
                file_path_string
            )

            text = editor_tab.get_text()

            file_path.write_text(
                text,
                encoding="utf-8",
            )

            document = (
                editor_tab.working_document
            )

            document.set_file_path(
                file_path
            )

            document.text = text
            document.mark_clean()

            self.tab_manager.close_tab(
                editor_tab
            )

        except Exception as error:
            print(
                f"Save before close error: {error}"
            )

    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)

        self.project_folder: Path | None = None
        self.build_manager = BuildManager()

        # QEdit persistent state.
        self.state_directory = (
            Path.home()
            / ".local"
            / "state"
            / "qedit"
        )

        self.session_manager = SessionManager(
            self.state_directory
        )

        self.tab_manager = TabManager(
            self.session_manager
        )

        self.tab_manager.set_close_request_callback(
            self.request_close_tab
        )

        self.tab_manager.notebook.connect(
            "switch-page",
            self._on_active_tab_changed,
        )

        self.set_default_size(1000, 700)

        # The application title no longer depends on the current document.
        self.set_title("Quar Edit")

        self.main_layout = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.menu_bar = EditorMenuBar()

        self.tab_manager.set_vexpand(True)
        self.tab_manager.set_hexpand(True)

        self.main_layout.append(self.menu_bar)
        self.main_layout.append(self.tab_manager)

        self.build_output_revealer = Gtk.Revealer()
        self.build_output_revealer.set_reveal_child(False)

        output_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        output_box.set_margin_start(6)
        output_box.set_margin_end(6)
        output_box.set_margin_bottom(6)

        output_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )
        output_title = Gtk.Label(label="Build Output")
        output_title.set_xalign(0.0)
        output_title.set_hexpand(True)
        close_output = Gtk.Button(label="×")
        close_output.connect(
            "clicked",
            lambda button: self.build_output_revealer.set_reveal_child(False),
        )
        output_header.append(output_title)
        output_header.append(close_output)

        self.build_output = Gtk.TextView()
        self.build_output.set_editable(False)
        self.build_output.set_cursor_visible(False)
        self.build_output.set_monospace(True)
        self.build_output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        output_scroll = Gtk.ScrolledWindow()
        output_scroll.set_min_content_height(150)
        output_scroll.set_max_content_height(260)
        output_scroll.set_child(self.build_output)

        output_box.append(output_header)
        output_box.append(output_scroll)
        self.build_output_revealer.set_child(output_box)
        self.main_layout.append(self.build_output_revealer)

        self.set_child(self.main_layout)

        language_manager.register_callback(
            self._on_language_changed
        )

        # Restore the previous editing session.
        self.tab_manager.restore_tabs()

        # A completely new QEdit installation still starts with one tab.
        if self.tab_manager.get_tab_count() == 0:
            self.tab_manager.create_tab()

        self._refresh_build_action_states()

    def _on_active_tab_changed(self, notebook, page, page_number) -> None:
        """Refresh language-dependent build actions after changing tabs."""
        self._refresh_build_action_states(page)

    def _refresh_build_action_states(self, editor_tab=None) -> None:
        """Enable Run / Interpret only for languages with an interpreter or VM."""
        if editor_tab is None:
            editor_tab = self.tab_manager.get_active_tab()

        profile = None
        if editor_tab is not None:
            document = editor_tab.working_document
            if document.file_path is not None:
                profile = profile_for_path(document.file_path)
            else:
                extension = getattr(editor_tab, "template_extension", None)
                if extension:
                    profile = next(
                        (item for item in PROFILES if extension in item.source_extensions),
                        None,
                    )

        can_interpret = (
            profile is not None
            and get_operation(profile, ("Interpret",)) is not None
        )

        app = self.get_application()
        if app is not None:
            run_action = app.lookup_action("run")
            if run_action is not None:
                run_action.set_enabled(can_interpret)

    def new_file(self) -> None:
        """Create a new persistent empty editor tab."""

        self.tab_manager.create_tab()

    def open_file(self) -> None:
        """Display a file chooser and open the selected file in a new tab."""

        dialog = Gtk.FileDialog()

        dialog.open(
            self,
            None,
            self._on_open_file_finished,
        )

    def _on_open_file_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
    ) -> None:
        """Load the selected file into a new persistent editor tab."""

        try:
            file = dialog.open_finish(result)

            if file is None:
                return

            file_path_string = file.get_path()

            if file_path_string is None:
                return

            file_path = Path(file_path_string)

            text = file_path.read_text(
                encoding="utf-8"
            )

            editor_tab = self.tab_manager.create_tab()

            editor_tab.working_document.set_file_path(
                file_path
            )

            editor_tab.set_text(
                text,
                modified=False,
            )

            # Store the opened state immediately so the tab can be restored
            # even if QEdit terminates before the user changes the document.
            editor_tab.save_checkpoint()

            self.session_manager.save_session()

            self._update_tab_label(
                editor_tab
            )

        except Exception as error:
            print(f"Open file error: {error}")

    def open_folder(self) -> None:
        """Display a chooser for selecting the current project folder."""

        dialog = Gtk.FileDialog()

        dialog.select_folder(
            self,
            None,
            self._on_open_folder_finished,
        )

    def _on_open_folder_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
    ) -> None:
        """Store the folder selected by the user."""

        try:
            folder = dialog.select_folder_finish(
                result
            )

            if folder is None:
                return

            folder_path_string = folder.get_path()

            if folder_path_string is None:
                return

            self.project_folder = Path(
                folder_path_string
            )

            print(
                f"Project folder: {self.project_folder}"
            )

        except Exception as error:
            print(f"Open folder error: {error}")

    def save_file(self) -> None:
        """Save the currently active tab to its source file."""

        editor_tab = self.tab_manager.get_active_tab()

        if editor_tab is None:
            return

        document = editor_tab.working_document

        if document.file_path is None:
            self.save_file_as()
            return

        try:
            text = editor_tab.get_text()

            document.file_path.write_text(
                text,
                encoding="utf-8",
            )

            document.text = text
            document.mark_clean()

            editor_tab.save_checkpoint()
            self.session_manager.save_session()

            self._update_tab_label(
                editor_tab
            )

        except Exception as error:
            print(f"Save file error: {error}")

    def save_file_as(self) -> None:
        """Display a dialog for saving the active tab to a new file."""

        editor_tab = self.tab_manager.get_active_tab()

        if editor_tab is None:
            return

        dialog = Gtk.FileDialog()
        dialog.set_filters(self._create_save_filters())

        # For an unnamed tab, propose its dynamic name.
        suggested_name = (
            editor_tab.get_base_display_name()
        )

        if suggested_name != "empty":
            dialog.set_initial_name(
                suggested_name
            )

        dialog.save(
            self,
            None,
            self._on_save_file_finished,
        )

    def _on_save_file_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
    ) -> None:
        """Save the active working document to the selected path."""

        try:
            file = dialog.save_finish(result)

            if file is None:
                return

            file_path_string = file.get_path()

            if file_path_string is None:
                return

            editor_tab = (
                self.tab_manager.get_active_tab()
            )

            if editor_tab is None:
                return

            file_path = Path(
                file_path_string
            )

            text = editor_tab.get_text()

            file_path.write_text(
                text,
                encoding="utf-8",
            )

            document = (
                editor_tab.working_document
            )

            document.set_file_path(
                file_path
            )

            document.text = text
            document.mark_clean()

            editor_tab.save_checkpoint()
            self.session_manager.save_session()

            self._update_tab_label(
                editor_tab
            )

        except Exception as error:
            print(f"Save file error: {error}")

    def _update_tab_label(
        self,
        editor_tab: EditorTab,
    ) -> None:
        """Request TabManager to refresh the visible tab label."""

        self.tab_manager.refresh_tab_label(
            editor_tab
        )

    def _create_save_filters(self) -> Gio.ListStore:
        """Return Save As filters derived from the language registry."""
        filters = Gio.ListStore.new(Gtk.FileFilter)

        all_files = Gtk.FileFilter()
        all_files.set_name("All Files (*.*)")
        all_files.add_pattern("*")
        filters.append(all_files)

        text_files = Gtk.FileFilter()
        text_files.set_name("Text Files (*.txt)")
        text_files.add_pattern("*.txt")
        filters.append(text_files)

        for profile in PROFILES:
            file_filter = Gtk.FileFilter()
            file_filter.set_name(
                f"{profile.display_name} Sources"
            )
            for extension in profile.extensions:
                file_filter.add_pattern(f"*{extension}")
            filters.append(file_filter)

        return filters

    def create_from_template(self, extension: str, content: str) -> None:
        """Create a new unsaved tab containing a source template."""
        editor_tab = self.tab_manager.create_tab()
        editor_tab.set_text(content, modified=True)
        editor_tab.template_extension = extension
        self._update_tab_label(editor_tab)
        self._refresh_build_action_states(editor_tab)

    def compile_active_file_debug(self) -> None:
        """Compile the active source in debug/fast mode."""
        self._execute_build_action("compile_debug")

    def compile_active_file_release(self) -> None:
        """Compile the active source in optimized/release mode."""
        self._execute_build_action("compile_release")

    def build_active_file(self) -> None:
        """Build the active source using the profile selected by its extension."""
        self._execute_build_action("build")

    def run_active_file(self) -> None:
        """Run or interpret the active source."""
        self._execute_build_action("run")

    def build_and_run_active_file(self) -> None:
        """Build the active source and run it only after a successful build."""
        self._execute_build_action("build_run")

    def _execute_build_action(self, action_name: str) -> None:
        """Save the source when possible, execute a build action and show output."""
        editor_tab = self.tab_manager.get_active_tab()
        if editor_tab is None:
            return

        document = editor_tab.working_document

        if document.file_path is None:
            self._show_build_message(
                "Build cannot start yet.\nSave the source file first so Quar Edit can identify its language."
            )
            return

        if document.modified:
            self.save_file()

        try:
            if action_name == "compile_debug":
                results = [self.build_manager.compile_debug(document.file_path)]
            elif action_name == "compile_release":
                results = [self.build_manager.compile_release(document.file_path)]
            elif action_name == "build":
                results = [self.build_manager.build(document.file_path)]
            elif action_name == "run":
                results = [self.build_manager.run(document.file_path)]
            else:
                results = self.build_manager.build_and_run(document.file_path)

            self._show_build_results(results)

        except Exception as error:
            self._show_build_message(f"Build error: {error}")

    def _show_build_results(self, results: list[BuildResult]) -> None:
        """Render command output and exit status in the bottom panel."""
        sections: list[str] = []

        for result in results:
            status = (
                "SUCCESS"
                if result.return_code == 0
                else f"FAILED (exit code {result.return_code})"
            )
            body = result.output if result.output else "(no output)"
            sections.append(
                f"{result.title}\n"
                f"$ {result.command}\n"
                f"{body}\n"
                f"{status}\n"
                f"Time: {result.duration_seconds:.6f} s"
            )

        self._show_build_message("\n\n".join(sections))

    def _show_build_message(self, message: str) -> None:
        """Show text in the Build Output panel."""
        buffer = self.build_output.get_buffer()
        buffer.set_text(message)
        self.build_output_revealer.set_reveal_child(True)

    def _on_language_changed(self) -> None:
        """Refresh localized interface elements."""

        self.menu_bar.rebuild()