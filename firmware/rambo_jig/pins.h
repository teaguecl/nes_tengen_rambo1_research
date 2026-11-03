// pins.h: the only place that knows how signals map to AVR port bits.
// Source: docs/j2_mega_pinmap.csv (Mega adapter). Do not hard-code bits elsewhere.
#pragma once
#include <Arduino.h>

// ---- Mega -> RAMBO (outputs) ----------------------------------------------
// CPU data bus D0-D7: PORTA, bit n = Dn (D22-D29).
#define DATA_PORT   PORTA
#define DATA_DDR    DDRA

// Control/address bits on PORTC (D30-D37). Bit order is routing order, not signal order.
#define CTRL_PORT   PORTC
#define CTRL_DDR    DDRC
#define BIT_M2        7   // D30
#define BIT_RW        6   // D31
#define BIT_ROMSEL_N  5   // D32
#define BIT_A0        4   // D33
#define BIT_A13       3   // D34
#define BIT_A14       2   // D35
#define BIT_PPU_A10   1   // D36
#define BIT_PPU_A11   0   // D37

#define M2_MASK        _BV(BIT_M2)
#define RW_MASK        _BV(BIT_RW)
#define ROMSEL_N_MASK  _BV(BIT_ROMSEL_N)
#define CPU_ADDR_MASK  (_BV(BIT_A0) | _BV(BIT_A13) | _BV(BIT_A14))
#define PPU_ADDR_MASK  (_BV(BIT_PPU_A10) | _BV(BIT_PPU_A11))

// PPU A12 on PD7 (D38). PD0 (D21, INT0) is /IRQ and must stay an input.
#define PPU_A12_PORT  PORTD
#define PPU_A12_DDR   DDRD
#define BIT_PPU_A12   7
#define PPU_A12_MASK  _BV(BIT_PPU_A12)

// Convert a CPU address ($8000-$FFFF) to the A0/A13/A14 bits on CTRL_PORT.
// A15 is implied by /ROMSEL low; A1-A12 are not wired to the RAMBO.
static inline uint8_t cpuAddrToCtrl(uint16_t addr) {
  uint8_t v = 0;
  if (addr & 0x0001) v |= _BV(BIT_A0);
  if (addr & 0x2000) v |= _BV(BIT_A13);
  if (addr & 0x4000) v |= _BV(BIT_A14);
  return v;
}

// ---- RAMBO pin 19 (flying lead) --------------------------------------------
// Mega D2 = PE4 -> 1 kohm -> RAMBO pin 19 net (SW1 contact 3A). SW1C must be OFF while this is used.
// Pin 19 is an input-style pad that the original board ties to GND (docs/findings.md F-043).
// Idle state is released (input, no pull-up) so it comes up undriven at reset.
#define P19_PORT   PORTE
#define P19_DDR    DDRE
#define P19_PIN    PINE
#define BIT_P19    4
#define P19_MASK   _BV(BIT_P19)

// mode: 0 = drive low, 1 = drive high, other = release (high impedance).
static inline void setPin19(uint8_t mode) {
  if (mode == 0)      { P19_PORT &= ~P19_MASK; P19_DDR |= P19_MASK; }
  else if (mode == 1) { P19_PORT |= P19_MASK;  P19_DDR |= P19_MASK; }
  else                { P19_DDR &= ~P19_MASK;  P19_PORT &= ~P19_MASK; }
}
static inline char pin19State() {
  if (!(P19_DDR & P19_MASK)) return 'Z';
  return (P19_PORT & P19_MASK) ? 'H' : 'L';
}

// ---- RAMBO -> Mega (inputs) -----------------------------------------------
// PORTG: PG2=PRG_A13, PG1=PRG_A14, PG0=PRG_A15
// PORTL: PL7=PRG_A16, PL6=PRG_A17, PL5=PRG_CE_N, PL4..PL0=CHR_A10..CHR_A14
// PORTB: PB3=CHR_A15, PB2=CHR_A16, PB1=CHR_A17, PB0=CIRAM_A10
// PORTD: PD0=IRQ_N (INT0, D21)
#define IRQ_PIN        21
#define IRQ_PIN_REG    PIND
#define BIT_IRQ_N      0

// Packed output word, in signal order (independent of port bit order).
enum OutBit : uint8_t {
  OUT_PRG_A13 = 0, OUT_PRG_A14, OUT_PRG_A15, OUT_PRG_A16, OUT_PRG_A17,
  OUT_PRG_CE_N,
  OUT_CHR_A10, OUT_CHR_A11, OUT_CHR_A12, OUT_CHR_A13,
  OUT_CHR_A14, OUT_CHR_A15, OUT_CHR_A16, OUT_CHR_A17,
  OUT_CIRAM_A10,
  OUT_IRQ_N,
  OUT_COUNT
};

static const char *const OUT_NAMES[OUT_COUNT] = {
  "PRG_A13", "PRG_A14", "PRG_A15", "PRG_A16", "PRG_A17",
  "PRG_CE_N",
  "CHR_A10", "CHR_A11", "CHR_A12", "CHR_A13",
  "CHR_A14", "CHR_A15", "CHR_A16", "CHR_A17",
  "CIRAM_A10",
  "IRQ_N"
};

#define PUT(word, port, pbit, sig) \
  do { if ((port) & _BV(pbit)) (word) |= (uint16_t)1 << (sig); } while (0)

// Pack raw port reads (PING, PINL, PINB, IRQ_PIN_REG) into the signal-ordered word.
static inline uint16_t packOutputs(uint8_t g, uint8_t l, uint8_t b, uint8_t d) {
  uint16_t w = 0;
  PUT(w, g, 2, OUT_PRG_A13);
  PUT(w, g, 1, OUT_PRG_A14);
  PUT(w, g, 0, OUT_PRG_A15);
  PUT(w, l, 7, OUT_PRG_A16);
  PUT(w, l, 6, OUT_PRG_A17);
  PUT(w, l, 5, OUT_PRG_CE_N);
  PUT(w, l, 4, OUT_CHR_A10);
  PUT(w, l, 3, OUT_CHR_A11);
  PUT(w, l, 2, OUT_CHR_A12);
  PUT(w, l, 1, OUT_CHR_A13);
  PUT(w, l, 0, OUT_CHR_A14);
  PUT(w, b, 3, OUT_CHR_A15);
  PUT(w, b, 2, OUT_CHR_A16);
  PUT(w, b, 1, OUT_CHR_A17);
  PUT(w, b, 0, OUT_CIRAM_A10);
  PUT(w, d, BIT_IRQ_N, OUT_IRQ_N);
  return w;
}

// Sample all RAMBO outputs. Ports are read back-to-back (not one instant).
static inline uint16_t readOutputs() {
  uint8_t g = PING, l = PINL, b = PINB, d = IRQ_PIN_REG;
  return packOutputs(g, l, b, d);
}

// Define every pin at the start of setup(). PORT is written before DDR so each
// output comes up at its idle level with no glitch.
// Idle: M2 low, R/W high, /ROMSEL high, data high (matches the cart pull-ups).
static inline void initPins() {
  CTRL_PORT = RW_MASK | ROMSEL_N_MASK;   // M2 low, A0/A13/A14/PPU A10/A11 low
  CTRL_DDR  = 0xFF;
  DATA_PORT = 0xFF;
  DATA_DDR  = 0xFF;
  PPU_A12_PORT &= ~PPU_A12_MASK;
  PPU_A12_DDR  |= PPU_A12_MASK;
  DDRG &= ~0x07; PORTG &= ~0x07;         // inputs, no internal pull-ups
  DDRL  = 0x00;  PORTL  = 0x00;
  DDRB &= ~0x0F; PORTB &= ~0x0F;
  DDRD &= ~_BV(BIT_IRQ_N); PORTD &= ~_BV(BIT_IRQ_N);  // cart has the 10k pull-up
  setPin19(2);                           // pin 19 released
}

// ---- Table of every Mega output, for pin-check ---------------------------
struct DrivePin {
  const char *name;
  volatile uint8_t *port;
  volatile uint8_t *pin;
  uint8_t mask;
  bool idleHigh;   // level set by initPins()
};

#define DRIVE_PIN(n, port, pin, bit, idle) { n, &port, &pin, _BV(bit), idle }
static const DrivePin DRIVE_PINS[] = {
  DRIVE_PIN("D0", PORTA, PINA, 0, true), DRIVE_PIN("D1", PORTA, PINA, 1, true),
  DRIVE_PIN("D2", PORTA, PINA, 2, true), DRIVE_PIN("D3", PORTA, PINA, 3, true),
  DRIVE_PIN("D4", PORTA, PINA, 4, true), DRIVE_PIN("D5", PORTA, PINA, 5, true),
  DRIVE_PIN("D6", PORTA, PINA, 6, true), DRIVE_PIN("D7", PORTA, PINA, 7, true),
  DRIVE_PIN("M2",       CTRL_PORT, PINC, BIT_M2,       false),
  DRIVE_PIN("RW",       CTRL_PORT, PINC, BIT_RW,       true),
  DRIVE_PIN("ROMSEL_N", CTRL_PORT, PINC, BIT_ROMSEL_N, true),
  DRIVE_PIN("A0",       CTRL_PORT, PINC, BIT_A0,       false),
  DRIVE_PIN("A13",      CTRL_PORT, PINC, BIT_A13,      false),
  DRIVE_PIN("A14",      CTRL_PORT, PINC, BIT_A14,      false),
  DRIVE_PIN("PPU_A10",  CTRL_PORT, PINC, BIT_PPU_A10,  false),
  DRIVE_PIN("PPU_A11",  CTRL_PORT, PINC, BIT_PPU_A11,  false),
  DRIVE_PIN("PPU_A12",  PPU_A12_PORT, PIND, BIT_PPU_A12, false),
};
#define DRIVE_PIN_COUNT (sizeof(DRIVE_PINS) / sizeof(DRIVE_PINS[0]))
