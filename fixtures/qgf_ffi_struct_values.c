#include <stdint.h>

typedef struct {
    int32_t x;
    double y;
    uint32_t flags;
} QGFPoint;

QGFPoint qgf_make_point(int32_t x, double y, uint32_t flags) {
    QGFPoint point = {x, y, flags};
    return point;
}

double qgf_point_sum(QGFPoint point) {
    return (double)point.x + point.y + (double)point.flags;
}

QGFPoint qgf_make_point_signed(int32_t x, double y, int32_t flags) {
    QGFPoint point = {x, y, (uint32_t)flags};
    return point;
}
