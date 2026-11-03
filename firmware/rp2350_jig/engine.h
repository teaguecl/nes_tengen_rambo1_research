#ifndef ENGINE_H
#define ENGINE_H
#include <stdint.h>
#include <stdbool.h>

#define ENG_MAX_STIM   (48u * 1024u)    // words (4 bytes) in the stimulus buffer
#define ENG_MAX_CAP    (64u * 1024u)    // words in the capture buffer

extern uint32_t eng_stim[ENG_MAX_STIM];
extern uint32_t eng_cap[ENG_MAX_CAP];
extern unsigned eng_nstim, eng_ncap;

typedef struct { bool ok; uint32_t fdebug; const char *why; } eng_result_t;

// Runs the loaded stimulus (eng_nstim words) and captures ncap words from the same cycle, at PIO clock divider `div` (1.0 = the system clock).
eng_result_t engine_run(unsigned ncap, float div);
#endif
