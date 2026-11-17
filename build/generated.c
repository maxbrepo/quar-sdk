#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

int main(void) {
    int32_t count = 10;
    int32_t other = 5;
    count = (count + (other * 2));
    printf("%d\n", count);
    (count + other);
    return 0;
}