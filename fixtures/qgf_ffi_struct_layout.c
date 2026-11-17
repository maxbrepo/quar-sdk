#include <stddef.h>
#include <stdint.h>

typedef struct {
    int32_t x;
    double y;
    uint32_t flags;
} QGFPoint;

size_t qgf_point_size(void) { return sizeof(QGFPoint); }
size_t qgf_point_alignment(void) { return _Alignof(QGFPoint); }
size_t qgf_point_x_offset(void) { return offsetof(QGFPoint, x); }
size_t qgf_point_y_offset(void) { return offsetof(QGFPoint, y); }
size_t qgf_point_flags_offset(void) { return offsetof(QGFPoint, flags); }
