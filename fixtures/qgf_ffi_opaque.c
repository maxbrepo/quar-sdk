#include <stdint.h>

static int32_t stored_value = 42;

void *qgf_get_handle(void) { return &stored_value; }
int32_t qgf_read_handle(void *handle) {
    if (handle != &stored_value) return -1;
    return *(int32_t *)handle;
}
void *qgf_null_handle(void) { return 0; }
