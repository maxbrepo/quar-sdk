#include <stdint.h>

typedef struct {
    int32_t x;
    double y;
    uint32_t flags;
} QGFOutPoint;

int32_t qgf_fill_point(QGFOutPoint *out) {
    if (!out) return -1;
    out->x = 20;
    out->y = 2.5;
    out->flags = 3;
    return 0;
}

int32_t qgf_fail_point(QGFOutPoint *out) {
    if (!out) return -1;
    out->x = 99;
    return 7;
}
