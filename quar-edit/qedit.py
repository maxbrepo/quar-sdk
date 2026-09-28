import gi
import json
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, Gtk
from lang.language_manager import language_manager
from settings.shortcuts import shortcut_manager
from ui.main_window import QuarEditWindow
from ui.preferences_window import PreferencesWindow
from build.build_settings_window import BuildSettingsWindow
from templates.template_registry import TEMPLATES


class QuarEditApplication(Gtk.Application):
    """Main QEdit GTK application."""

    def __init__(self) -> None:
        super().__init__(
            application_id="org.visualquar.edit"
        )

        self.window: QuarEditWindow | None = None
        self.preferences_window: PreferencesWindow | None = None
        self.build_settings_window: BuildSettingsWindow | None = None
        self.settings_path = Path.home() / ".config" / "quar-edit" / "settings.json"
        self.current_theme = self._load_saved_theme()
        self.css_provider: Gtk.CssProvider | None = None

        self._load_theme()
        self._create_actions()
        self._apply_shortcuts()

    def _load_theme(self) -> None:
        """Load the QEdit CSS theme and apply it to the current display."""

        theme_path = (
            Path(__file__).resolve().parent
            / "themes"
            / "qedit.css"
        )

        if not theme_path.exists():
            print(f"QEdit theme not found: {theme_path}")
            return

        display = Gdk.Display.get_default()

        if display is None:
            print("QEdit display is not available.")
            return

        provider = Gtk.CssProvider()

        try:
            provider.load_from_path(str(theme_path))
        except Exception as error:
            print(f"QEdit theme load error: {error}")
            return

        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.css_provider = provider

    def _create_actions(self) -> None:
        """Create the application actions currently implemented by QEdit."""
        self._add_action("new_file", self._on_new_file)
        self._add_action("open_file", self._on_open_file)
        self._add_action("open_folder", self._on_open_folder)
        self._add_action("save", self._on_save)
        self._add_action("save_as", self._on_save_as)
        self._add_action("close_tab", self._on_close_tab)
        self._add_action("exit", self._on_exit)
        self._add_action("preferences", self._on_preferences)
        self._add_action("language_english", self._on_language_english)
        self._add_action("language_italian", self._on_language_italian)
        self._add_action("language_spanish", self._on_language_spanish)
        self._add_action("language_portuguese_brazil", self._on_language_portuguese_brazil)
        self._add_action("language_japanese", self._on_language_japanese)
        self._add_action("language_chinese_simplified", self._on_language_chinese_simplified)
        self._add_action("language_chinese_traditional", self._on_language_chinese_traditional)
        self._add_action("language_korean", self._on_language_korean)
        self._add_action("language_hindi", self._on_language_hindi)
        self._add_action("language_french", self._on_language_french)
        self._add_action("language_arabic", self._on_language_arabic)
        self._add_action("language_russian", self._on_language_russian)
        self._add_action("language_german", self._on_language_german)
        self._add_action("language_turkish", self._on_language_turkish)
        self._add_action("language_indonesian", self._on_language_indonesian)
        self._add_action("language_vietnamese", self._on_language_vietnamese)
        self._add_action("language_polish", self._on_language_polish)
        self._add_action("language_bengali", self._on_language_bengali)
        self._add_action("language_thai", self._on_language_thai)
        self._add_action("language_persian", self._on_language_persian)
        self._add_action("language_urdu", self._on_language_urdu)
        self._add_action("language_ukrainian", self._on_language_ukrainian)
        self._add_action("language_dutch", self._on_language_dutch)
        self._add_action("language_greek", self._on_language_greek)
        self._add_action("language_czech", self._on_language_czech)
        self._add_action("language_romanian", self._on_language_romanian)
        self._add_action("theme_light", self._on_theme_light)
        self._add_action("theme_dark", self._on_theme_dark)
        self._add_action("theme_dark_blue", self._on_theme_dark_blue)
        self._add_action("theme_vim", self._on_theme_vim)
        self._add_action("build_settings", self._on_build_settings)
        for index, template_data in enumerate(TEMPLATES):
            self._add_action(
                f"new_template_{index}",
                self._make_template_action(template_data),
            )
        self._add_action("compile_debug", self._on_compile_debug)
        self._add_action("compile_release", self._on_compile_release)
        self._add_action("build", self._on_build)
        self._add_action("run", self._on_run)
        self._add_action("build_run", self._on_build_run)

    def _apply_shortcuts(self) -> None:
        """Apply all configured keyboard shortcuts."""
        for shortcut in shortcut_manager.get_all():
            accelerators: list[str] = []
            if shortcut.accelerator:
                accelerators.append(shortcut.accelerator)
            self.set_accels_for_action(shortcut.action_id, accelerators)

    def _add_action(self, name: str, callback) -> None:
        """Create a Gio action and connect it to a callback."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def do_activate(self) -> None:
        """Create and display the main QEdit window."""
        if self.window is None:
            self.window = QuarEditWindow(self)
            self._set_theme(self.current_theme, save=False)
        self.window.present()

    def _on_new_file(self, action, parameter) -> None:
        """Request creation of a new document."""
        if self.window is not None:
            self.window.new_file()

    def _on_open_file(self, action, parameter) -> None:
        """Request opening a file."""
        if self.window is not None:
            self.window.open_file()

    def _on_open_folder(self, action, parameter) -> None:
        """Request opening a working folder."""
        if self.window is not None:
            self.window.open_folder()

    def _on_save(self, action, parameter) -> None:
        """Save the current document."""
        if self.window is not None:
            self.window.save_file()

    def _on_save_as(self, action, parameter) -> None:
        """Save the current document to a selected path."""
        if self.window is not None:
            self.window.save_file_as()

    def _on_close_tab(self, action, parameter) -> None:
        """Close the currently active editor tab."""
        if self.window is not None:
            self.window.close_current_tab()

    def _on_preferences(self, action, parameter) -> None:
        """Open the QEdit Preferences window."""
        if self.preferences_window is None:
            self.preferences_window = PreferencesWindow(self)
            self.preferences_window.connect("close-request", self._on_preferences_closed)
        self.preferences_window.present()

    def _on_preferences_closed(self, window: Gtk.Window) -> bool:
        """Release the Preferences window after it is closed."""
        self.preferences_window = None
        return False

    def _on_language_english(self, action, parameter) -> None:
        """Change the interface language to English."""
        language_manager.set_language("eng")

    def _on_language_italian(self, action, parameter) -> None:
        """Change the interface language to Italian."""
        language_manager.set_language("ita")

    def _load_saved_theme(self) -> str:
        """Load the last selected theme; Dark Blue is the first-run default."""
        if not self.settings_path.exists():
            return "dark-blue"
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            theme = str(data.get("theme", "dark-blue"))
            if theme in {"light", "dark", "dark-blue", "vim"}:
                return theme
        except Exception as error:
            print(f"Theme settings load error: {error}")
        return "dark-blue"

    def _save_theme(self) -> None:
        """Persist the active theme."""
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(
                json.dumps({"theme": self.current_theme}, indent=2),
                encoding="utf-8",
            )
        except Exception as error:
            print(f"Theme settings save error: {error}")

    def _set_theme(self, theme_name: str, save: bool = True) -> None:
        """Apply a QEdit theme and optionally persist it."""
        if self.window is None:
            return
        for css_class in ("qedit-theme-light","qedit-theme-dark","qedit-theme-dark-blue","qedit-theme-vim"):
            self.window.remove_css_class(css_class)
        self.window.add_css_class(f"qedit-theme-{theme_name}")
        self.current_theme = theme_name
        if save:
            self._save_theme()

    def _on_language_spanish(self, action, parameter) -> None:
        language_manager.set_language("spa")

    def _on_language_portuguese_brazil(self, action, parameter) -> None:
        language_manager.set_language("por")

    def _on_language_japanese(self, action, parameter) -> None:
        language_manager.set_language("jpn")

    def _on_language_chinese_simplified(self, action, parameter) -> None:
        language_manager.set_language("zho_hans")

    def _on_language_chinese_traditional(self, action, parameter) -> None:
        language_manager.set_language("zho_hant")

    def _on_language_korean(self, action, parameter) -> None:
        language_manager.set_language("kor")

    def _on_language_hindi(self, action, parameter) -> None:
        language_manager.set_language("hin")

    def _on_language_french(self, action, parameter) -> None:
        language_manager.set_language("fra")

    def _on_language_arabic(self, action, parameter) -> None:
        language_manager.set_language("ara")

    def _on_language_russian(self, action, parameter) -> None:
        language_manager.set_language("rus")

    def _on_language_german(self, action, parameter) -> None:
        language_manager.set_language("deu")

    def _on_language_turkish(self, action, parameter) -> None:
        language_manager.set_language("tur")

    def _on_language_indonesian(self, action, parameter) -> None:
        language_manager.set_language("ind")

    def _on_language_vietnamese(self, action, parameter) -> None:
        language_manager.set_language("vie")

    def _on_language_polish(self, action, parameter) -> None:
        language_manager.set_language("pol")

    def _on_language_bengali(self, action, parameter) -> None:
        language_manager.set_language("ben")

    def _on_language_thai(self, action, parameter) -> None:
        language_manager.set_language("tha")

    def _on_language_persian(self, action, parameter) -> None:
        language_manager.set_language("fas")

    def _on_language_urdu(self, action, parameter) -> None:
        language_manager.set_language("urd")

    def _on_language_ukrainian(self, action, parameter) -> None:
        language_manager.set_language("ukr")

    def _on_language_dutch(self, action, parameter) -> None:
        language_manager.set_language("nld")

    def _on_language_greek(self, action, parameter) -> None:
        language_manager.set_language("ell")

    def _on_language_czech(self, action, parameter) -> None:
        language_manager.set_language("ces")

    def _on_language_romanian(self, action, parameter) -> None:
        language_manager.set_language("ron")

    def _on_theme_light(self, action, parameter) -> None:
        self._set_theme("light")

    def _on_theme_dark(self, action, parameter) -> None:
        self._set_theme("dark")

    def _on_theme_dark_blue(self, action, parameter) -> None:
        """Apply the dark blue QEdit theme."""
        self._set_theme("dark-blue")

    def _on_theme_vim(self, action, parameter) -> None:
        self._set_theme("vim")

    def _make_template_action(self, template_data):
        """Return an action callback that creates one source template."""
        label_text, extension, content = template_data

        def create_template(action, parameter) -> None:
            if self.window is not None:
                self.window.create_from_template(extension, content)

        return create_template

    def _on_compile_debug(self, action, parameter) -> None:
        """Compile the active source in debug/fast mode."""
        if self.window is not None:
            self.window.compile_active_file_debug()

    def _on_compile_release(self, action, parameter) -> None:
        """Compile the active source in optimized/release mode."""
        if self.window is not None:
            self.window.compile_active_file_release()

    def _on_build(self, action, parameter) -> None:
        """Build the active source."""
        if self.window is not None:
            self.window.build_active_file()

    def _on_run(self, action, parameter) -> None:
        """Run or interpret the active source."""
        if self.window is not None:
            self.window.run_active_file()

    def _on_build_run(self, action, parameter) -> None:
        """Build and then run the active source."""
        if self.window is not None:
            self.window.build_and_run_active_file()

    def _on_build_settings(self, action, parameter) -> None:
        """Open the Build Settings prototype."""
        if self.build_settings_window is None:
            self.build_settings_window = BuildSettingsWindow(self)
            self.build_settings_window.connect("close-request", self._on_build_settings_closed)
        self.build_settings_window.present()

    def _on_build_settings_closed(self, window: Gtk.Window) -> bool:
        """Release the Build Settings window after closing."""
        self.build_settings_window = None
        return False

    def _on_exit(self, action, parameter) -> None:
        """Close QEdit."""
        if self.window is not None:
            self.window.tab_manager.checkpoint_all()
        self.quit()


def main() -> int:
    """Start QEdit and return the GTK application exit status."""
    app = QuarEditApplication()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
