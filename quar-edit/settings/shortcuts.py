from dataclasses import dataclass


@dataclass
class ShortcutDefinition:
    """Describe one configurable QEdit keyboard shortcut."""

    action_id: str
    label_key: str
    default_accelerator: str
    accelerator: str


class ShortcutManager:
    """Store and manage QEdit keyboard shortcuts."""

    def __init__(self) -> None:
        self._shortcuts: dict[str, ShortcutDefinition] = {}

        self._register(
            "app.new_file",
            "file.new",
            "<Control>n",
        )

        self._register(
            "app.open_file",
            "file.open",
            "<Control>o",
        )

        self._register(
            "app.save",
            "file.save",
            "<Control>s",
        )

        self._register(
            "app.save_as",
            "file.save_as",
            "<Control><Shift>s",
        )

        self._register(
            "app.find",
            "edit.find",
            "<Control>f",
        )

        self._register(
            "app.close_tab",
            "tab.close",
            "<Control>w",
        )

        self._register(
            "app.exit",
            "file.exit",
            "<Control>q",
        )

    def _register(
        self,
        action_id: str,
        label_key: str,
        accelerator: str,
    ) -> None:
        """Register one shortcut with its default accelerator."""
        self._shortcuts[action_id] = ShortcutDefinition(
            action_id=action_id,
            label_key=label_key,
            default_accelerator=accelerator,
            accelerator=accelerator,
        )

    def get_all(self) -> tuple[ShortcutDefinition, ...]:
        """Return all shortcut definitions."""
        return tuple(self._shortcuts.values())

    def get_accelerator(self, action_id: str) -> str:
        """Return the accelerator assigned to an action."""
        shortcut = self._shortcuts.get(action_id)

        if shortcut is None:
            return ""

        return shortcut.accelerator

    def set_accelerator(
        self,
        action_id: str,
        accelerator: str,
    ) -> bool:
        """Assign an accelerator and return True on success."""
        shortcut = self._shortcuts.get(action_id)

        if shortcut is None:
            return False

        shortcut.accelerator = accelerator
        return True

    def find_conflict(
        self,
        accelerator: str,
        excluded_action_id: str,
    ) -> ShortcutDefinition | None:
        """Return another action already using the accelerator."""
        if not accelerator:
            return None

        for shortcut in self._shortcuts.values():
            if shortcut.action_id == excluded_action_id:
                continue

            if shortcut.accelerator == accelerator:
                return shortcut

        return None

    def remove_accelerator(self, action_id: str) -> bool:
        """Remove the shortcut assigned to an action."""
        return self.set_accelerator(action_id, "")

    def restore_defaults(self) -> None:
        """Restore every shortcut to its default accelerator."""
        for shortcut in self._shortcuts.values():
            shortcut.accelerator = shortcut.default_accelerator


shortcut_manager = ShortcutManager()