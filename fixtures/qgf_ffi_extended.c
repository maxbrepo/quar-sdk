#include <stdint.h>

int64_t qgf_add64(int64_t a, int64_t b) { return a + b; }
uint64_t qgf_add_unsigned64(uint64_t a, uint64_t b) { return a + b; }
float qgf_multiply_f32(float a, float b) { return a * b; }
double qgf_multiply_f64(double a, double b) { return a * b; }
static int32_t last_value = 0;
void qgf_set_value(int32_t value) { last_value = value; }
int32_t qgf_get_value(void) { return last_value; }
