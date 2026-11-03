// RAMBO-1 adapter pin map (docs/j2_rp2350_pinmap.csv, checked against the KiCad netlist on 2026-11-02: all 33 signals match).
// ALL bit and GPIO mapping lives here; no other file hard-codes a pin.
#ifndef PINS_H
#define PINS_H

// Control (plain GPIO, owned by the CPU firmware, never by a PIO)
#define PIN_PWR_EN   4    // high: Q1 switches the cart's 5 V (J2 pin 1). R2 pulls it low at reset.
#define PIN_OE_EN    15   // high: the three 74HCT541 drivers (stimulus) are enabled. R4 pulls it low at reset.

// Stimulus: the chip's 17 inputs, GPIO26..42 contiguous, bit 0 = GPIO26. Through 74HCT541 (U2: D0-D7, U3: M2..PPU A11, U4: PPU A12).
#define STIM_BASE    26
#define STIM_COUNT   17
enum {
    S_D0, S_D1, S_D2, S_D3, S_D4, S_D5, S_D6, S_D7,
    S_M2, S_RW, S_ROMSEL, S_A0, S_A13, S_A14, S_PPU_A10, S_PPU_A11, S_PPU_A12
};
#define STIM_IDLE    0x1FFFFu     // all high: what the cart's pull-ups hold when the drivers are off (M2, R/W, /ROMSEL high: no cycle)

// The chip's outputs: through 74LVC541A (U5: CHR A12-A17, CIRAM, /IRQ; U6: PRG A13-A17, /CE, CHR A10, A11).
typedef struct { const char *name; unsigned char gpio; unsigned char j2; } sig_t;

static const sig_t STIM_SIG[STIM_COUNT] = {
    {"D0", 26, 3}, {"D1", 27, 4}, {"D2", 28, 5}, {"D3", 29, 6}, {"D4", 30, 7}, {"D5", 31, 8}, {"D6", 32, 9}, {"D7", 33, 10},
    {"M2", 34, 12}, {"RW", 35, 13}, {"ROMSEL", 36, 14}, {"A0", 37, 15}, {"A13", 38, 16}, {"A14", 39, 17},
    {"PPUA10", 40, 19}, {"PPUA11", 41, 20}, {"PPUA12", 42, 21},
};

#define OUT_COUNT 16
static const sig_t OUT_SIG[OUT_COUNT] = {
    {"PRGA13", 18, 23}, {"PRGA14", 17, 24}, {"PRGA15", 16, 25}, {"PRGA16", 47, 26}, {"PRGA17", 46, 27}, {"CE", 45, 28},
    {"CHRA10", 44, 30}, {"CHRA11", 43, 31}, {"CHRA12", 14, 32}, {"CHRA13", 13, 33}, {"CHRA14", 12, 34},
    {"CHRA15", 23, 35}, {"CHRA16", 22, 36}, {"CHRA17", 21, 37}, {"CIRAM", 20, 39}, {"IRQ", 19, 40},
};

#endif
