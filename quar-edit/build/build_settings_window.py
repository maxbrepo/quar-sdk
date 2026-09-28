from __future__ import annotations
import platform
import gi
gi.require_version("Gtk","4.0")
from gi.repository import Gtk
from build.build_profiles import PROFILES

class BuildSettingsWindow(Gtk.ApplicationWindow):
    """Prototype editor for language/build associations."""
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("Quar Edit - Build Settings")
        self.set_default_size(820,600)
        self.platform_name = "windows" if platform.system()=="Windows" else "linux"

        root=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=0)
        self.languages=Gtk.ListBox()
        self.languages.set_size_request(180,-1)
        self.languages.connect("row-selected",self._selected)
        for profile in PROFILES:
            row=Gtk.ListBoxRow()
            label=Gtk.Label(label=profile.display_name)
            label.set_xalign(0.0)
            label.set_margin_start(12); label.set_margin_end(12)
            label.set_margin_top(9); label.set_margin_bottom(9)
            row.set_child(label); row.profile=profile
            self.languages.append(row)

        left=Gtk.ScrolledWindow()
        left.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        left.set_child(self.languages)

        self.details=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.details.set_margin_start(18); self.details.set_margin_end(18)
        self.details.set_margin_top(18); self.details.set_margin_bottom(18)
        right=Gtk.ScrolledWindow()
        right.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        right.set_hexpand(True); right.set_vexpand(True)
        right.set_child(self.details)
        root.append(left); root.append(right); self.set_child(root)

        first=self.languages.get_row_at_index(0)
        if first is not None: self.languages.select_row(first)

    def _clear(self) -> None:
        child=self.details.get_first_child()
        while child is not None:
            nxt=child.get_next_sibling(); self.details.remove(child); child=nxt

    def _field(self,label_text:str,value:str) -> None:
        label=Gtk.Label(label=label_text); label.set_xalign(0.0)
        label.add_css_class("qedit-build-field-label")
        entry=Gtk.Entry(); entry.set_text(value); entry.set_hexpand(True)
        self.details.append(label); self.details.append(entry)

    def _selected(self,list_box,row) -> None:
        if row is None: return
        p=row.profile; self._clear()
        title=Gtk.Label(); title.set_markup(f"<b>{p.display_name}</b>"); title.set_xalign(0.0)
        title.add_css_class("qedit-build-title"); self.details.append(title)
        self._field("Source extensions", ", ".join(p.source_extensions))
        if p.header_extensions:
            self._field("Header extensions", ", ".join(p.header_extensions))
        self._field("Compiler",p.compiler)
        self._field("Interpreter / VM",p.interpreter)
        self._field("Linker", p.linker)
        platform_label=Gtk.Label(label=f"Commands for: {self.platform_name.capitalize()}")
        platform_label.set_xalign(0.0); platform_label.add_css_class("qedit-build-platform")
        self.details.append(platform_label)
        for op in p.operations:
            heading=Gtk.Label()
            extra=" - optional tool" if op.optional else ""
            heading.set_markup(f"<b>{op.name}</b> ({op.kind}){extra}")
            heading.set_xalign(0.0); self.details.append(heading)
            self._field("Command", op.windows if self.platform_name=="windows" else op.linux)
        help_label=Gtk.Label(label="Variables: {source}, {source_dir}, {filename}, {basename}, {extension}, {output}, {project_dir}")
        help_label.set_wrap(True); help_label.set_xalign(0.0); help_label.add_css_class("qedit-build-help")
        self.details.append(help_label)
