/* SDL3 polling adapter: status 1=event, 0=empty, -1=invalid argument. */
#include <stdint.h>
#include <SDL3/SDL.h>

int32_t vq_sdl3_poll_event(SDL_Event *out) {
    if (out == NULL) return -1;
    return SDL_PollEvent(out) ? 1 : 0;
}

/* The owner must initialize the event subsystem before polling. */
int32_t vq_sdl3_init_events(void) {
    return SDL_InitSubSystem(SDL_INIT_EVENTS) ? 1 : 0;
}

void vq_sdl3_quit_events(void) {
    SDL_QuitSubSystem(SDL_INIT_EVENTS);
}

const char *vq_sdl3_last_error(void) {
    return SDL_GetError();
}

/* Test-only injection hook: send a quit event through SDL's actual queue. */
int32_t vq_sdl3_test_push_quit(void) {
    SDL_Event event = {0};
    event.type = SDL_EVENT_QUIT;
    return SDL_PushEvent(&event) ? 1 : 0;
}

/* Test-only hooks: enqueue typed events through the actual SDL3 queue. */
int32_t vq_sdl3_test_push_key(int32_t pressed, int32_t scancode, int32_t keycode) {
    SDL_Event event = {0};
    event.type = pressed ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
    event.key.scancode = (SDL_Scancode)scancode;
    event.key.key = (SDL_Keycode)keycode;
    return SDL_PushEvent(&event) ? 1 : 0;
}

int32_t vq_sdl3_test_push_motion(float x, float y) {
    SDL_Event event = {0};
    event.type = SDL_EVENT_MOUSE_MOTION;
    event.motion.x = x;
    event.motion.y = y;
    return SDL_PushEvent(&event) ? 1 : 0;
}
