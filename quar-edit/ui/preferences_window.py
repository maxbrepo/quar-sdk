import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from lang.language_manager import get_string
from settings.shortcuts import ShortcutDefinition, shortcut_manager


class PreferencesWindow(Gtk.Window):
    """Display and edit QEdit preferences."""

    def __init__(self, application: Gtk.Application) -> None:
        super().__init__()

        self.application = application
        self.selected_action_id: str | None = None
        self.capture_action_id: str | None = None

        # Keys currently captured for the new shortcut.
        self.captured_keys: list[str] = []

        # GTK modifier mask captured for the shortcut.
        self.captured_modifiers = Gdk.ModifierType(0)

        # Final non-modifier key.
        self.captured_keyval: int | None = None

        self.set_title(get_string("settings.title"))
        self.set_default_size(680, 480)
        self.set_modal(True)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )

        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)

        title = Gtk.Label(
            label=get_string("settings.shortcuts")
        )
        title.set_xalign(0.0)

        main_box.append(title)

        # Shortcut list.
        self.shortcut_list = Gtk.ListBox()
        self.shortcut_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self.shortcut_list.connect(
            "row-selected",
            self._on_row_selected,
        )

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.shortcut_list)

        main_box.append(scrolled)

        # Shortcut capture area.
        self.capture_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self.key_boxes: list[Gtk.Label] = []

        for index in range(3):
            key_box = Gtk.Label(label="")

            key_box.set_size_request(90, 36)
            key_box.set_xalign(0.5)
            key_box.add_css_class("frame")

            self.key_boxes.append(key_box)
            self.capture_box.append(key_box)

            if index < 2:
                plus = Gtk.Label(label="+")
                self.capture_box.append(plus)

        self.capture_box.set_visible(False)

        main_box.append(self.capture_box)

        self.capture_message = Gtk.Label(label="")
        self.capture_message.set_xalign(0.0)

        main_box.append(self.capture_message)

        # Buttons.
        button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self.change_button = Gtk.Button(
            label=get_string("settings.shortcuts.change")
        )

        self.remove_button = Gtk.Button(
            label=get_string("settings.shortcuts.remove")
        )

        self.restore_button = Gtk.Button(
            label=get_string("settings.shortcuts.restore")
        )

        self.change_button.connect(
            "clicked",
            self._on_change_clicked,
        )

        self.remove_button.connect(
            "clicked",
            self._on_remove_clicked,
        )

        self.restore_button.connect(
            "clicked",
            self._on_restore_clicked,
        )

        button_box.append(self.change_button)
        button_box.append(self.remove_button)
        button_box.append(self.restore_button)

        main_box.append(button_box)

        self.set_child(main_box)

        # Capture keyboard input at window level.
        key_controller = Gtk.EventControllerKey()

        key_controller.connect(
            "key-pressed",
            self._on_key_pressed,
        )

        self.add_controller(key_controller)

        self._rebuild_list()

    def _rebuild_list(self) -> None:
        """Rebuild the visible list of keyboard shortcuts."""

        while True:
            row = self.shortcut_list.get_row_at_index(0)

            if row is None:
                break

            self.shortcut_list.remove(row)

        for shortcut in shortcut_manager.get_all():
            row = self._create_shortcut_row(shortcut)
            self.shortcut_list.append(row)

    def _create_shortcut_row(
        self,
        shortcut: ShortcutDefinition,
    ) -> Gtk.ListBoxRow:
        """Create one row representing a configurable shortcut."""

        row = Gtk.ListBoxRow()
        row.action_id = shortcut.action_id

        content = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )

        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)

        action_label = Gtk.Label(
            label=get_string(shortcut.label_key)
        )

        action_label.set_xalign(0.0)
        action_label.set_hexpand(True)

        shortcut_label = Gtk.Label(
            label=self._format_accelerator(
                shortcut.accelerator
            )
        )

        shortcut_label.set_xalign(1.0)

        content.append(action_label)
        content.append(shortcut_label)

        row.set_child(content)

        return row

    def _format_accelerator(
        self,
        accelerator: str,
    ) -> str:
        """Return a human-readable representation of an accelerator."""

        if not accelerator:
            return "—"

        success, key, modifiers = Gtk.accelerator_parse(
            accelerator
        )

        if not success:
            return accelerator

        return Gtk.accelerator_get_label(
            key,
            modifiers,
        )

    def _on_row_selected(
        self,
        list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        """Store the action selected by the user."""

        if row is None:
            self.selected_action_id = None
            return

        self.selected_action_id = row.action_id

    def _on_change_clicked(
        self,
        button: Gtk.Button,
    ) -> None:
        """Start capturing a new shortcut."""

        if self.selected_action_id is None:
            return

        self.capture_action_id = self.selected_action_id

        self.captured_keys = []
        self.captured_modifiers = Gdk.ModifierType(0)
        self.captured_keyval = None

        self._clear_key_boxes()

        self.capture_box.set_visible(True)

        self.capture_message.set_text(
            get_string("settings.shortcuts.press")
        )

    def _on_remove_clicked(
        self,
        button: Gtk.Button,
    ) -> None:
        """Remove the selected shortcut."""

        if self.selected_action_id is None:
            return

        shortcut_manager.remove_accelerator(
            self.selected_action_id
        )

        self._apply_shortcuts()
        self._rebuild_list()

    def _on_restore_clicked(
        self,
        button: Gtk.Button,
    ) -> None:
        """Restore all default keyboard shortcuts."""

        shortcut_manager.restore_defaults()

        self._apply_shortcuts()
        self._rebuild_list()

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        """Capture keys and apply the shortcut only after Enter."""

        if self.capture_action_id is None:
            return False

        # Escape cancels the operation.
        if keyval == Gdk.KEY_Escape:
            self._cancel_capture()
            return True

        # Enter confirms the captured shortcut.
        if keyval in (
            Gdk.KEY_Return,
            Gdk.KEY_KP_Enter,
        ):
            self._confirm_capture()
            return True

        # Delete or Backspace clears the current capture.
        if keyval in (
            Gdk.KEY_BackSpace,
            Gdk.KEY_Delete,
        ):
            self.captured_keys = []
            self.captured_modifiers = Gdk.ModifierType(0)
            self.captured_keyval = None

            self._clear_key_boxes()

            return True

        modifier_names = self._get_modifier_names(state)

        key_name = Gdk.keyval_name(keyval)

        if key_name is None:
            return True

        # Modifier keys are represented through the modifier mask.
        if self._is_modifier_key(keyval):
            self._update_capture_boxes(
                modifier_names,
                None,
            )
            return True

        self.captured_modifiers = (
            state & Gtk.accelerator_get_default_mod_mask()
        )

        self.captured_keyval = keyval

        self._update_capture_boxes(
            self._get_modifier_names(
                self.captured_modifiers
            ),
            key_name,
        )

        return True

    def _get_modifier_names(
        self,
        state: Gdk.ModifierType,
    ) -> list[str]:
        """Return human-readable names for active modifiers."""

        names: list[str] = []

        if state & Gdk.ModifierType.CONTROL_MASK:
            names.append("Ctrl")

        if state & Gdk.ModifierType.SHIFT_MASK:
            names.append("Shift")

        if state & Gdk.ModifierType.ALT_MASK:
            names.append("Alt")

        if state & Gdk.ModifierType.SUPER_MASK:
            names.append("Super")

        return names

    def _is_modifier_key(
        self,
        keyval: int,
    ) -> bool:
        """Return True when keyval represents only a modifier key."""

        return keyval in (
            Gdk.KEY_Control_L,
            Gdk.KEY_Control_R,
            Gdk.KEY_Shift_L,
            Gdk.KEY_Shift_R,
            Gdk.KEY_Alt_L,
            Gdk.KEY_Alt_R,
            Gdk.KEY_Super_L,
            Gdk.KEY_Super_R,
        )

    def _update_capture_boxes(
        self,
        modifiers: list[str],
        key_name: str | None,
    ) -> None:
        """Display captured modifiers and key in the three boxes."""

        values = modifiers.copy()

        if key_name is not None:
            values.append(key_name.upper())

        self.captured_keys = values[:3]

        self._clear_key_boxes()

        for index, value in enumerate(self.captured_keys):
            self.key_boxes[index].set_text(value)

    def _clear_key_boxes(self) -> None:
        """Clear all visible shortcut capture boxes."""

        for key_box in self.key_boxes:
            key_box.set_text("")

    def _confirm_capture(self) -> None:
        """Validate and assign the captured shortcut."""

        if self.capture_action_id is None:
            return

        if self.captured_keyval is None:
            return

        accelerator = Gtk.accelerator_name(
            self.captured_keyval,
            self.captured_modifiers,
        )

        conflict = shortcut_manager.find_conflict(
            accelerator,
            self.capture_action_id,
        )

        if conflict is not None:
            conflict_name = get_string(
                conflict.label_key
            )

            self.capture_message.set_text(
                f"{get_string('settings.shortcuts.conflict')} "
                f"{conflict_name}"
            )

            return

        shortcut_manager.set_accelerator(
            self.capture_action_id,
            accelerator,
        )

        self._apply_shortcuts()
        self._rebuild_list()
        self._finish_capture()

    def _cancel_capture(self) -> None:
        """Cancel shortcut capture without changing the assignment."""

        self._finish_capture()

    def _finish_capture(self) -> None:
        """Return Preferences to its normal state."""

        self.capture_action_id = None
        self.captured_keys = []
        self.captured_modifiers = Gdk.ModifierType(0)
        self.captured_keyval = None

        self._clear_key_boxes()

        self.capture_box.set_visible(False)
        self.capture_message.set_text("")

    def _apply_shortcuts(self) -> None:
        """Apply current shortcut assignments to QEdit."""

        for shortcut in shortcut_manager.get_all():
            accelerators: list[str] = []

            if shortcut.accelerator:
                accelerators.append(
                    shortcut.accelerator
                )

            self.application.set_accels_for_action(
                shortcut.action_id,
                accelerators,
            )