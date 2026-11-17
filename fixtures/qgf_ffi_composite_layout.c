#include <stddef.h>
#include <stdint.h>

typedef struct { int32_t x; double y; } Point;
typedef union { uint64_t bits; double value; } Number;
typedef struct { uint32_t tag; Point points[3]; Number number; int32_t samples[4]; } Packet;

size_t qgf_packet_size(void) { return sizeof(Packet); }
size_t qgf_packet_alignment(void) { return _Alignof(Packet); }
size_t qgf_packet_tag_offset(void) { return offsetof(Packet, tag); }
size_t qgf_packet_points_offset(void) { return offsetof(Packet, points); }
size_t qgf_packet_number_offset(void) { return offsetof(Packet, number); }
size_t qgf_packet_samples_offset(void) { return offsetof(Packet, samples); }
size_t qgf_point_size(void) { return sizeof(Point); }
size_t qgf_number_size(void) { return sizeof(Number); }
