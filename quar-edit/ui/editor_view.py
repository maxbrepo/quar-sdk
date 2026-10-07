import gi
from collections.abc import Callable

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Gtk, Pango, PangoCairo


ModifiedCallback = Callable[[], None]


class EditorView(Gtk.Box):
    """Display one text editor with a graphical line-number gutter."""

    MIN_GUTTER_WIDTH = 54
    GUTTER_HORIZONTAL_PADDING = 8
    DEFAULT_FONT_SIZE = 12
    MIN_FONT_SIZE = 7
    MAX_FONT_SIZE = 40

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
        )

        self.set_hexpand(True)
        self.set_vexpand(True)

        # The line-number gutter is graphical only. It has no text buffer,
        # cannot receive focus, and therefore cannot interfere with the
        # document cursor or scrolling.
        self.line_number_gutter = Gtk.DrawingArea()
        self.line_number_gutter.set_can_focus(False)
        self.line_number_gutter.set_content_width(
            self.MIN_GUTTER_WIDTH
        )
        self.line_number_gutter.set_hexpand(False)
        self.line_number_gutter.set_vexpand(True)
        self.line_number_gutter.add_css_class(
            "qedit-line-number-gutter"
        )
        self.line_number_gutter.set_draw_func(
            self._draw_line_numbers
        )

        # Create the only real text view used by the document.
        self.editor = Gtk.TextView()
        self.editor.set_monospace(True)
        self.editor.set_wrap_mode(Gtk.WrapMode.NONE)
        self.editor.set_left_margin(8)
        self.editor.add_css_class("qedit-editor")

        self.buffer = self.editor.get_buffer()

        self.editor_scroll = Gtk.ScrolledWindow()
        self.editor_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC,
        )
        self.editor_scroll.set_hexpand(True)
        self.editor_scroll.set_vexpand(True)
        self.editor_scroll.set_child(self.editor)

        self.append(self.line_number_gutter)
        self.append(self.editor_scroll)

        self._modified_callback: ModifiedCallback | None = None
        self._ignore_changes = False
        self._font_size = self.DEFAULT_FONT_SIZE
        self._syntax_highlighter = None
        self._highlight_refreshing = False

        self._scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        self._scroll_controller.connect("scroll", self._on_editor_scroll)
        self.editor.add_controller(self._scroll_controller)
        self._apply_source_font_size()

        self.buffer.connect(
            "changed",
            self._on_buffer_changed,
        )
        self.buffer.connect(
            "mark-set",
            self._on_buffer_mark_set,
        )

        # Redraw the gutter whenever the real editor viewport moves.
        vertical_adjustment = (
            self.editor_scroll.get_vadjustment()
        )
        vertical_adjustment.connect(
            "value-changed",
            self._on_scroll_changed,
        )

        self._update_gutter_width()

    def get_text_view(self) -> Gtk.TextView:
        """Return the Gtk.TextView used by the document editor."""
        return self.editor

    def get_text(self) -> str:
        """Return all text currently stored in the document buffer."""
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()

        return self.buffer.get_text(
            start,
            end,
            True,
        )

    def set_text(self, text: str) -> None:
        """Replace editor contents without marking the document modified."""
        self._ignore_changes = True

        try:
            self.buffer.set_text(text)
            self._update_gutter_width()
            self.line_number_gutter.queue_draw()
            self._refresh_syntax_highlighting()
        finally:
            self._ignore_changes = False

    def set_syntax_highlighter(self, callback) -> None:
        """Install or clear the callback that styles the current text buffer."""
        self._syntax_highlighter = callback
        self._refresh_syntax_highlighting()

    def _refresh_syntax_highlighting(self) -> None:
        """Refresh syntax tags once, preventing TextBuffer signal re-entry."""
        if self._syntax_highlighter is None or self._highlight_refreshing:
            return
        self._highlight_refreshing = True
        try:
            self._syntax_highlighter(self.buffer)
        finally:
            self._highlight_refreshing = False

    def clear(self) -> None:
        """Clear the editor without marking the document modified."""
        self.set_text("")

    def set_modified_callback(
        self,
        callback: ModifiedCallback,
    ) -> None:
        """Register the function called after a user text modification."""
        self._modified_callback = callback

    def get_cursor_offset(self) -> int:
        """Return the current document cursor offset."""
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(
            insert_mark
        )
        return cursor_iter.get_offset()

    def set_cursor_offset(
        self,
        offset: int,
    ) -> None:
        """Restore the document cursor to a valid character offset."""
        end_offset = self.buffer.get_char_count()
        safe_offset = max(
            0,
            min(offset, end_offset),
        )

        cursor_iter = self.buffer.get_iter_at_offset(
            safe_offset
        )
        self.buffer.place_cursor(cursor_iter)

    def get_vertical_scroll_position(self) -> float:
        """Return the current vertical viewport position."""
        return self.editor_scroll.get_vadjustment().get_value()

    def set_vertical_scroll_position(
        self,
        position: float,
    ) -> None:
        """Restore the vertical viewport position within valid bounds."""
        adjustment = self.editor_scroll.get_vadjustment()

        maximum = max(
            adjustment.get_lower(),
            adjustment.get_upper()
            - adjustment.get_page_size(),
        )

        safe_position = max(
            adjustment.get_lower(),
            min(position, maximum),
        )

        adjustment.set_value(safe_position)

    def get_horizontal_scroll_position(self) -> float:
        """Return the current horizontal viewport position."""
        return self.editor_scroll.get_hadjustment().get_value()

    def set_horizontal_scroll_position(
        self,
        position: float,
    ) -> None:
        """Restore the horizontal viewport position within valid bounds."""
        adjustment = self.editor_scroll.get_hadjustment()

        maximum = max(
            adjustment.get_lower(),
            adjustment.get_upper()
            - adjustment.get_page_size(),
        )

        safe_position = max(
            adjustment.get_lower(),
            min(position, maximum),
        )

        adjustment.set_value(safe_position)

    def _apply_source_font_size(self) -> None:
        """Apply the current zoom level only to the source text."""
        self.editor.set_css_classes([
            "qedit-editor",
            f"qedit-source-size-{self._font_size}",
        ])

    def _on_editor_scroll(
        self,
        controller: Gtk.EventControllerScroll,
        dx: float,
        dy: float,
    ) -> bool:
        """Zoom source text with Ctrl + mouse wheel."""
        modifiers = controller.get_current_event_state()
        if not (modifiers & Gdk.ModifierType.CONTROL_MASK):
            return False
        old_size = self._font_size
        if dy < 0:
            self._font_size = min(self.MAX_FONT_SIZE, self._font_size + 1)
        elif dy > 0:
            self._font_size = max(self.MIN_FONT_SIZE, self._font_size - 1)
        if self._font_size != old_size:
            self._apply_source_font_size()
            self._update_gutter_width()
            self.line_number_gutter.queue_draw()
        return True

    def _on_buffer_changed(
        self,
        buffer: Gtk.TextBuffer,
    ) -> None:
        """Refresh the gutter and notify QEdit after a text change."""
        if self._highlight_refreshing:
            return

        self._update_gutter_width()
        self.line_number_gutter.queue_draw()
        self._refresh_syntax_highlighting()

        if self._ignore_changes:
            return

        if self._modified_callback is not None:
            self._modified_callback()

    def _on_buffer_mark_set(
        self,
        buffer: Gtk.TextBuffer,
        location: Gtk.TextIter,
        mark: Gtk.TextMark,
    ) -> None:
        """Redraw the gutter when the cursor position changes."""
        if mark == self.buffer.get_insert():
            self.line_number_gutter.queue_draw()

    def _on_scroll_changed(
        self,
        adjustment: Gtk.Adjustment,
    ) -> None:
        """Redraw line numbers when the document viewport scrolls."""
        self.line_number_gutter.queue_draw()

    def _update_gutter_width(self) -> None:
        """Resize the gutter when the document needs more number digits."""
        line_count = max(
            1,
            self.buffer.get_line_count(),
        )
        digit_count = len(str(line_count))

        # Keep the gutter synchronized with source zoom. Line numbers scale
        # with the source font and the gutter expands when more space is needed.
        approximate_digit_width = max(
            7,
            int(self._font_size * 0.72),
        )

        requested_width = max(
            self.MIN_GUTTER_WIDTH,
            (digit_count * approximate_digit_width)
            + (self.GUTTER_HORIZONTAL_PADDING * 2),
        )

        self.line_number_gutter.set_content_width(
            requested_width
        )

    def _draw_line_numbers(
        self,
        drawing_area: Gtk.DrawingArea,
        context,
        width: int,
        height: int,
    ) -> None:
        """Draw only the line numbers currently visible in the editor."""
        visible_rect = self.editor.get_visible_rect()
        line_count = max(
            1,
            self.buffer.get_line_count(),
        )

        layout = drawing_area.create_pango_layout("")
        font_description = Pango.FontDescription(
            f"Monospace {self._font_size}"
        )
        layout.set_font_description(
            font_description
        )

        style_context = drawing_area.get_style_context()
        foreground = style_context.get_color()
        context.set_source_rgba(
            foreground.red,
            foreground.green,
            foreground.blue,
            foreground.alpha,
        )

        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        current_line = cursor_iter.get_line()

        for line_index in range(line_count):
            _, line_iter = self.buffer.get_iter_at_line(
                line_index
            )

            line_y, line_height = (
                self.editor.get_line_yrange(
                    line_iter
                )
            )

            screen_y = (
                line_y
                - visible_rect.y
            )

            if screen_y + line_height < 0:
                continue

            if screen_y > height:
                break

            line_text = str(
                line_index + 1
            )

            layout.set_text(
                line_text,
                -1,
            )

            text_width, text_height = (
                layout.get_pixel_size()
            )

            x = (
                width
                - self.GUTTER_HORIZONTAL_PADDING
                - text_width
            )

            y = (
                screen_y
                + max(
                    0,
                    (line_height - text_height) / 2,
                )
            )

            if line_index == current_line:
                context.save()
                context.set_source_rgba(
                    foreground.red,
                    foreground.green,
                    foreground.blue,
                    0.55,
                )
                context.set_line_width(1.0)
                context.rectangle(
                    x - 4,
                    y - 1,
                    text_width + 8,
                    text_height + 2,
                )
                context.stroke()
                context.restore()
                context.set_source_rgba(
                    foreground.red,
                    foreground.green,
                    foreground.blue,
                    foreground.alpha,
                )

            context.move_to(
                x,
                y,
            )
            PangoCairo.show_layout(
                context,
                layout,
            )
