#include <stdint.h>
typedef struct { int32_t x; double y; } Point;
typedef union { uint64_t bits; double value; } Number;
typedef struct { uint32_t tag; Point points[3]; Number number; int32_t samples[4]; } Packet;
int32_t qgf_fill_packet(Packet *out) {
    if (!out) return 9;
    out->tag = 42;
    out->points[0].x = 7;
    out->points[0].y = 2.5;
    out->number.bits = UINT64_C(0x1122334455667788);
    out->samples[0] = -3;
    return 0;
}
int32_t qgf_fail_packet(Packet *out) { if (out) out->tag = 99; return 7; }
