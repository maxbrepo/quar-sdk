#include <stdint.h>
#include <string.h>
int32_t qgf_utf8_length(const char *text) { return text ? (int32_t)strlen(text) : -1; }
int32_t qgf_utf8_match(const char *text) { return text && strcmp(text, "caff\xc3\xa8") == 0; }
