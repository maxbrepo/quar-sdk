#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t type;
    uint32_t code;
    uint64_t payload[3];
} QgfEvent;

size_t qgf_event_size(void) { return sizeof(QgfEvent); }
size_t qgf_event_alignment(void) { return _Alignof(QgfEvent); }
size_t qgf_event_type_offset(void) { return offsetof(QgfEvent, type); }
size_t qgf_event_code_offset(void) { return offsetof(QgfEvent, code); }
int32_t qgf_poll_event(QgfEvent *event) {
    if (event == NULL) return -1;
    event->type = 0x100;
    event->code = 42;
    return 1;
}
