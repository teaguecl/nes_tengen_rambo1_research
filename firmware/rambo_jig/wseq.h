// wseq.h: types for timed pin-state sequences (kept out of the .ino so Arduino's generated
// function prototypes can see them).
#pragma once
#include <Arduino.h>

// Port values are precomputed when the step is added so playback is just loads and OUTs.
struct Step { uint8_t ctrl, dataPort, dataDdr, portd, ticks, flags; };
#define STEP_MAX     48
#define SAMPLE_MAX   32
#define F_SAMPLE     0x01

struct SeqState { bool m2, rw, romsel; uint16_t addr; uint8_t d; bool dz, a12; };
struct RawSample { uint8_t g, l, b, d; };
