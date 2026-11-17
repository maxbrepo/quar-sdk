#include <stdint.h>
#include <stdlib.h>

void *qgf_create_handle(void) {
    int32_t *value = malloc(sizeof(*value));
    if (value != NULL) *value = 42;
    return value;
}
int32_t qgf_read_allocated(void *handle) {
    return *(int32_t *)handle;
}
void qgf_destroy_handle(void *handle) {
    free(handle);
}
