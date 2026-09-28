from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from templates.template_registry import TEMPLATES


class TemplateWindow(Gtk.ApplicationWindow):
    """Display all source templates in a left-side language list."""

    def __init__(self, app: Gtk.Application, create_callback) -> None:
        super().__init__(application=app)
        self.set_title("Quar Edit - New from Template")
        self.set_default_size(760, 520)
        self.create_callback = create_callback

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        self.template_list = Gtk.ListBox()
        self.template_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.template_list.set_size_request(230, -1)
        self.template_list.connect("row-selected", self._on_row_selected)
        self.template_list.connect("row-activated", self._on_row_activated)

        for label_text, extension, content in TEMPLATES:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=label_text)
            label.set_xalign(0.0)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(9)
            label.set_margin_bottom(9)
            row.set_child(label)
            row.template_data = (label_text, extension, content)
            self.template_list.append(row)

        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_child(self.template_list)
        root.append(left_scroll)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        details.set_margin_start(18)
        details.set_margin_end(18)
        details.set_margin_top(18)
        details.set_margin_bottom(18)
        details.set_hexpand(True)

        self.title_label = Gtk.Label()
        self.title_label.set_xalign(0.0)
        details.append(self.title_label)

        self.extension_label = Gtk.Label()
        self.extension_label.set_xalign(0.0)
        details.append(self.extension_label)

        preview_title = Gtk.Label(label="Template preview")
        preview_title.set_xalign(0.0)
        details.append(preview_title)

        self.preview = Gtk.TextView()
        self.preview.set_editable(False)
        self.preview.set_cursor_visible(False)
        self.preview.set_monospace(True)
        self.preview.set_wrap_mode(Gtk.WrapMode.NONE)

        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_hexpand(True)
        preview_scroll.set_vexpand(True)
        preview_scroll.set_child(self.preview)
        details.append(preview_scroll)

        create_button = Gtk.Button(label="Create")
        create_button.set_halign(Gtk.Align.END)
        create_button.connect("clicked", self._on_create_clicked)
        details.append(create_button)

        root.append(details)
        self.set_child(root)

        first = self.template_list.get_row_at_index(0)
        if first is not None:
            self.template_list.select_row(first)

    def _on_row_selected(self, list_box, row) -> None:
        """Refresh the right-side preview for the selected language."""
        if row is None:
            return
        label_text, extension, content = row.template_data
        self.title_label.set_markup(f"<b>{label_text}</b>")
        self.extension_label.set_text(f"File extension: {extension}")
        self.preview.get_buffer().set_text(content)

    def _on_row_activated(self, list_box, row) -> None:
        """Create a document when a language row is double-clicked."""
        self._create(row)

    def _on_create_clicked(self, button) -> None:
        """Create the currently selected source template."""
        row = self.template_list.get_selected_row()
        if row is not None:
            self._create(row)

    def _create(self, row) -> None:
        """Send the selected template to the main editor window."""
        _, extension, content = row.template_data
        self.create_callback(extension, content)
        self.close()
