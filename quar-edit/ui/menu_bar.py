import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

from lang.language_manager import get_string
from templates.template_registry import TEMPLATES


class EditorMenuBar(Gtk.PopoverMenuBar):
    def __init__(self) -> None:
        super().__init__()
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the complete menu bar using the active language."""

        menu_model = Gio.Menu()

        menu_model.append_submenu(
            get_string("menu.file"),
            self._create_file_menu(),
        )

        menu_model.append_submenu(
            get_string("menu.edit"),
            self._create_edit_menu(),
        )

        menu_model.append_submenu(
            get_string("menu.view"),
            self._create_view_menu(),
        )

        menu_model.append_submenu(
            get_string("menu.build"),
            self._create_build_menu(),
        )

        menu_model.append_submenu(
            get_string("menu.help"),
            self._create_help_menu(),
        )

        self.set_menu_model(menu_model)

    def _create_file_menu(self) -> Gio.Menu:
        """Create and return the File menu."""

        menu = Gio.Menu()

        new_section = Gio.Menu()

        new_section.append(
            get_string("file.new"),
            "app.new_file",
        )

        template_menu = Gio.Menu()
        for index, template_data in enumerate(TEMPLATES):
            label_text, extension, content = template_data
            template_menu.append(
                label_text,
                f"app.new_template_{index}",
            )

        new_section.append_submenu(
            "Template",
            template_menu,
        )

        new_section.append(
            get_string("file.new_project"),
            "app.new_project",
        )

        open_section = Gio.Menu()

        open_section.append(
            get_string("file.open"),
            "app.open_file",
        )

        open_section.append(
            get_string("file.open_folder"),
            "app.open_folder",
        )

        open_section.append(
            get_string("file.open_project"),
            "app.open_project",
        )

        save_section = Gio.Menu()

        close_section = Gio.Menu()

        close_section.append(
            get_string("tab.close"),
            "app.close_tab",
        )

        save_section.append(
            get_string("file.save"),
            "app.save",
        )

        save_section.append(
            get_string("file.save_as"),
            "app.save_as",
        )

        exit_section = Gio.Menu()

        exit_section.append(
            get_string("file.exit"),
            "app.exit",
        )

        menu.append_section(None, new_section)
        menu.append_section(None, open_section)
        menu.append_section(None, save_section)
        menu.append_section(None, close_section)
        menu.append_section(None, exit_section)

        return menu

    def _create_edit_menu(self) -> Gio.Menu:
        """Create and return the Edit menu."""

        menu = Gio.Menu()

        history_section = Gio.Menu()

        history_section.append(
            get_string("edit.undo"),
            "app.undo",
        )

        history_section.append(
            get_string("edit.redo"),
            "app.redo",
        )

        clipboard_section = Gio.Menu()

        clipboard_section.append(
            get_string("edit.cut"),
            "app.cut",
        )

        clipboard_section.append(
            get_string("edit.copy"),
            "app.copy",
        )

        clipboard_section.append(
            get_string("edit.paste"),
            "app.paste",
        )

        search_section = Gio.Menu()

        search_section.append(
            get_string("edit.find"),
            "app.find",
        )

        search_section.append(
            get_string("edit.replace"),
            "app.replace",
        )

        preferences_section = Gio.Menu()

        preferences_section.append(
            get_string("edit.preferences"),
            "app.preferences",
        )

        menu.append_section(None, history_section)
        menu.append_section(None, clipboard_section)
        menu.append_section(None, search_section)
        menu.append_section(None, preferences_section)

        return menu

    def _create_view_menu(self) -> Gio.Menu:
        """Create and return the View menu."""

        menu = Gio.Menu()

        interface_section = Gio.Menu()

        interface_section.append(
            get_string("view.toolbar"),
            "app.toolbar",
        )

        interface_section.append(
            get_string("view.status_bar"),
            "app.status_bar",
        )

        menu.append_section(None, interface_section)

        language_menu = Gio.Menu()

        language_menu.append(
            get_string("language.english"),
            "app.language_english",
        )

        language_menu.append(
            get_string("language.italian"),
            "app.language_italian",
        )

        language_menu.append(get_string("language.spanish"), "app.language_spanish")
        language_menu.append(get_string("language.portuguese_brazil"), "app.language_portuguese_brazil")
        language_menu.append(get_string("language.japanese"), "app.language_japanese")
        language_menu.append(get_string("language.chinese_simplified"), "app.language_chinese_simplified")
        language_menu.append(get_string("language.chinese_traditional"), "app.language_chinese_traditional")
        language_menu.append(get_string("language.korean"), "app.language_korean")
        language_menu.append(get_string("language.hindi"), "app.language_hindi")
        language_menu.append(get_string("language.french"), "app.language_french")
        language_menu.append(get_string("language.arabic"), "app.language_arabic")
        language_menu.append(get_string("language.russian"), "app.language_russian")
        language_menu.append(get_string("language.german"), "app.language_german")
        language_menu.append(get_string("language.turkish"), "app.language_turkish")
        language_menu.append(get_string("language.indonesian"), "app.language_indonesian")
        language_menu.append(get_string("language.vietnamese"), "app.language_vietnamese")
        language_menu.append(get_string("language.polish"), "app.language_polish")
        language_menu.append(get_string("language.bengali"), "app.language_bengali")
        language_menu.append(get_string("language.thai"), "app.language_thai")
        language_menu.append(get_string("language.persian"), "app.language_persian")
        language_menu.append(get_string("language.urdu"), "app.language_urdu")
        language_menu.append(get_string("language.ukrainian"), "app.language_ukrainian")
        language_menu.append(get_string("language.dutch"), "app.language_dutch")
        language_menu.append(get_string("language.greek"), "app.language_greek")
        language_menu.append(get_string("language.czech"), "app.language_czech")
        language_menu.append(get_string("language.romanian"), "app.language_romanian")

        menu.append_submenu(
            get_string("view.language"),
            language_menu,
        )

        theme_menu = Gio.Menu()
        theme_menu.append("Light", "app.theme_light")
        theme_menu.append("Dark", "app.theme_dark")
        theme_menu.append("Dark Blue", "app.theme_dark_blue")
        theme_menu.append("Vim", "app.theme_vim")
        menu.append_submenu("Theme", theme_menu)

        return menu

    def _create_build_menu(self) -> Gio.Menu:
        """Create and return the Build menu."""

        menu = Gio.Menu()

        menu.append("Compile (Debug)", "app.compile_debug")
        menu.append("Compile", "app.compile_release")
        menu.append(get_string("build.build"), "app.build")

        menu.append(
            "Run / Interpret",
            "app.run",
        )

        menu.append(
            get_string("build.build_run"),
            "app.build_run",
        )

        settings_section = Gio.Menu()
        settings_section.append("Build Settings...", "app.build_settings")
        menu.append_section(None, settings_section)

        return menu

    def _create_help_menu(self) -> Gio.Menu:
        """Create and return the Help menu."""

        menu = Gio.Menu()

        menu.append(
            get_string("help.about"),
            "app.about",
        )

        return menu