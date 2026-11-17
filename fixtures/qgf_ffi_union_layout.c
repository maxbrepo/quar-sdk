#include <stddef.h>
#include <stdint.h>

union QGFNativeUnion {
    int32_t signed_value;
    uint64_t unsigned_value;
    double decimal_value;
};

size_t qgf_union_size(void) { return sizeof(union QGFNativeUnion); }
size_t qgf_union_alignment(void) { return _Alignof(union QGFNativeUnion); }
size_t qgf_union_signed_offset(void) { return offsetof(union QGFNativeUnion, signed_value); }
size_t qgf_union_unsigned_offset(void) { return offsetof(union QGFNativeUnion, unsigned_value); }
size_t qgf_union_decimal_offset(void) { return offsetof(union QGFNativeUnion, decimal_value); }
