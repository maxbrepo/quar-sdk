/* Compile against installed SDL3 headers; never assume SDL2 layouts. */
#include <stddef.h>
#include <stdio.h>
#include <SDL3/SDL.h>

int main(void) {
    printf("{\"size\":%zu,\"alignment\":%zu,\"offsets\":{"
           "\"type\":%zu,\"key_scancode\":%zu,\"key_key\":%zu,"
           "\"motion_x\":%zu,\"motion_y\":%zu},"
           "\"event_ids\":{\"keydown\":%u,\"keyup\":%u,\"motion\":%u,\"quit\":%u}}\n",
           sizeof(SDL_Event), _Alignof(SDL_Event),
           offsetof(SDL_Event, type),
           offsetof(SDL_Event, key.scancode),
           offsetof(SDL_Event, key.key),
           offsetof(SDL_Event, motion.x),
           offsetof(SDL_Event, motion.y),
           (unsigned)SDL_EVENT_KEY_DOWN,
           (unsigned)SDL_EVENT_KEY_UP,
           (unsigned)SDL_EVENT_MOUSE_MOTION,
           (unsigned)SDL_EVENT_QUIT);
    return 0;
}
