import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from lang.eng import get_string


class EditorToolbar(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
        )

        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self.new_button = self._create_button("toolbar.new.long")
        self.open_button = self._create_button("toolbar.open.long")
        self.save_button = self._create_button("toolbar.save.long")

        self.append(self.new_button)
        self.append(self.open_button)
        self.append(self.save_button)

    def _create_button(self, text_key: str) -> Gtk.Button:
        """Create and return a toolbar button using a localized label."""
        label = get_string(text_key)
        return Gtk.Button(label=label)