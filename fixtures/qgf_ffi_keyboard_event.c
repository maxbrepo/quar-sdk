/* Compiler-measured keyboard-event fixture; intentionally NOT SDL_Event. */
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t type;
    int32_t scancode;
    int32_t sym;
    uint32_t reserved;
    uint64_t payload;
} QgfKeyboardEvent;

size_t qgf_keyboard_size(void) { return sizeof(QgfKeyboardEvent); }
size_t qgf_keyboard_alignment(void) { return _Alignof(QgfKeyboardEvent); }
size_t qgf_keyboard_type_offset(void) { return offsetof(QgfKeyboardEvent, type); }
size_t qgf_keyboard_scancode_offset(void) { return offsetof(QgfKeyboardEvent, scancode); }
size_t qgf_keyboard_sym_offset(void) { return offsetof(QgfKeyboardEvent, sym); }
int32_t qgf_poll_keyboard(QgfKeyboardEvent *event) {
    if (!event) return -1;
    *event = (QgfKeyboardEvent){0};
    event->type = 0x300;
    event->scancode = 4;
    event->sym = -42;
    return 1;
}
