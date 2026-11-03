// RAMBO-1 jig firmware (Arduino Mega 2560). Serial 115200, one command per line.
// All pin/bit knowledge lives in pins.h.
#include "pins.h"
#include "wseq.h"

static bool argHex(const char *s, uint32_t &out);
static bool argDec(const char *s, uint32_t &out);
static void printHex(uint32_t v, uint8_t digits);
static void printOutputsWord(uint16_t w);

static volatile uint16_t irqCount = 0;
static void onIrq() { irqCount++; }

// ---- bus primitives -------------------------------------------------------
// Shadow of PORTC so PPU A10/A11 survive CPU-bus operations.
static uint8_t ppuBits = 0;

static inline void ctrl(uint8_t m2, uint8_t rw, uint8_t romselN, uint8_t addrBits) {
  CTRL_PORT = (m2 ? M2_MASK : 0) | (rw ? RW_MASK : 0) |
              (romselN ? ROMSEL_N_MASK : 0) | addrBits | ppuBits;
}

static inline void setA12(bool v) {
  if (v) PPU_A12_PORT |= PPU_A12_MASK; else PPU_A12_PORT &= ~PPU_A12_MASK;
}

// One idle CPU cycle: R/W high, /ROMSEL high, M2 high then low.
static void clockM2(uint32_t n) {
  while (n--) {
    ctrl(1, 1, 1, 0);
    ctrl(0, 1, 1, 0);
  }
}

// CPU write to $8000-$FFFF (see docs/hardware.md, "Emulating a CPU write").
static void cpuWrite(uint16_t addr, uint8_t data) {
  uint8_t a = cpuAddrToCtrl(addr);
  ctrl(0, 0, 1, a);          // 1. R/W low, address set, M2 low, /ROMSEL high
  DATA_PORT = data;          // 2. data
  ctrl(1, 0, 1, a);          // 3. M2 high,
  ctrl(1, 0, 0, a);          //    then /ROMSEL low
  ctrl(1, 0, 1, a);          // 4. /ROMSEL high,
  ctrl(0, 0, 1, a);          //    then M2 low
  ctrl(0, 1, 1, a);          // 5. R/W high (data stays driven)
}

// CPU read cycle at `addr`; returns the RAMBO outputs sampled while M2 is high and, for
// $8000-$FFFF, /ROMSEL is low (the phase in which PRG /CE is expected to be active).
// Only A0/A13/A14 are wired, so addresses below $8000 just leave /ROMSEL high.
// The data lines stay driven by the Mega: the RAMBO has no data outputs.
static uint16_t cpuRead(uint16_t addr) {
  uint8_t a = cpuAddrToCtrl(addr);
  ctrl(0, 1, 1, a);                  // R/W high, address set, M2 low, /ROMSEL high
  ctrl(1, 1, 1, a);                  // M2 high
  if (addr >= 0x8000) ctrl(1, 1, 0, a);   // /ROMSEL low
  delayMicroseconds(2);              // let the outputs settle before sampling
  uint16_t w = readOutputs();
  ctrl(1, 1, 1, a);                  // /ROMSEL high,
  ctrl(0, 1, 1, a);                  // then M2 low
  return w;
}

// ---- wseq: timed pin-state sequences --------------------------------------
// A list of steps is built with "wseq add" and played back with interrupts off. Within a step the
// data lines are written first, then the control port, then PPU A12 (a few cycles apart). A step
// lasts (per-step overhead) + 4 * T cycles; "wseq run" reports total cycles so the overhead can be
// measured. Nominal tick = 4 cycles = 250 ns.
static Step steps[STEP_MAX];
static uint8_t stepCount = 0;
static SeqState seqCur;
static RawSample samples[SAMPLE_MAX];
static uint8_t sampleStep[SAMPLE_MAX];

static void seqClear() {
  stepCount = 0;
  seqCur = { false, true, true, 0xE000, 0xFF, false, (bool)(PPU_A12_PORT & PPU_A12_MASK) };
}

static uint8_t seqCtrl(const SeqState &s) {
  return (s.m2 ? M2_MASK : 0) | (s.rw ? RW_MASK : 0) | (s.romsel ? ROMSEL_N_MASK : 0) |
         cpuAddrToCtrl(s.addr) | ppuBits;
}

// True if the step is a register write (M2 high, R/W low, /ROMSEL low) at an address other than $E000.
static bool stepIsRiskyWrite(const Step &st) {
  if (!(st.ctrl & M2_MASK) || (st.ctrl & RW_MASK) || (st.ctrl & ROMSEL_N_MASK)) return false;
  return (st.ctrl & CPU_ADDR_MASK) != (_BV(BIT_A13) | _BV(BIT_A14));
}

// Parse one "KEY=value" (or "S") token into the state under construction. Returns false if bad.
static bool seqField(const char *t, SeqState &s, uint8_t &ticks, bool &sample) {
  if (!strcmp(t, "S")) { sample = true; return true; }
  const char *eq = strchr(t, '=');
  if (!eq) return false;
  char key[8]; size_t kl = eq - t;
  if (kl == 0 || kl >= sizeof(key)) return false;
  memcpy(key, t, kl); key[kl] = 0;
  const char *v = eq + 1;
  uint32_t n;
  if (!strcmp(key, "D") && (v[0] == 'Z' || v[0] == 'z') && !v[1]) { s.dz = true; return true; }
  bool hex = !strcmp(key, "A") || !strcmp(key, "D");
  if (!(hex ? argHex(v, n) : argDec(v, n))) return false;
  if (!strcmp(key, "M2"))          { if (n > 1) return false; s.m2 = n; }
  else if (!strcmp(key, "RW"))     { if (n > 1) return false; s.rw = n; }
  else if (!strcmp(key, "ROMSEL")) { if (n > 1) return false; s.romsel = n; }
  else if (!strcmp(key, "A12"))    { if (n > 1) return false; s.a12 = n; }
  else if (!strcmp(key, "A"))      { if (n > 0xFFFF) return false; s.addr = n; }
  else if (!strcmp(key, "D"))      { if (n > 0xFF) return false; s.d = n; s.dz = false; }
  else if (!strcmp(key, "T"))      { if (n > 255) return false; ticks = n; }
  else return false;
  return true;
}

static void seqPrintStep(uint8_t i) {
  const Step &st = steps[i];
  Serial.print(i); Serial.print(F(": M2=")); Serial.print((st.ctrl >> BIT_M2) & 1);
  Serial.print(F(" RW=")); Serial.print((st.ctrl >> BIT_RW) & 1);
  Serial.print(F(" ROMSEL=")); Serial.print((st.ctrl >> BIT_ROMSEL_N) & 1);
  Serial.print(F(" A0/A13/A14=")); Serial.print((st.ctrl >> BIT_A0) & 1);
  Serial.print((st.ctrl >> BIT_A13) & 1); Serial.print((st.ctrl >> BIT_A14) & 1);
  Serial.print(F(" D=")); if (!st.dataDdr) Serial.print('Z'); else printHex(st.dataPort, 2);
  Serial.print(F(" A12=")); Serial.print((st.portd & PPU_A12_MASK) ? 1 : 0);
  Serial.print(F(" T=")); Serial.print(st.ticks);
  if (st.flags & F_SAMPLE) Serial.print(F(" S"));
  Serial.println();
}

// Play the list. Returns total Timer1 cycles (saturates at 65535 and sets *overflow).
static uint16_t seqRun(uint8_t &nSamples, bool &overflow) {
  uint8_t sreg = SREG; cli();
  uint8_t a1 = TCCR1A, b1 = TCCR1B; uint16_t c1 = TCNT1;
  TCCR1A = 0; TCCR1B = 0; TCNT1 = 0; TIFR1 = _BV(TOV1);
  uint8_t ns = 0;
  const Step *p = steps;
  const Step *end = steps + stepCount;
  TCCR1B = _BV(CS10);                       // clk/1, normal mode
  while (p != end) {
    uint8_t ctrlV = p->ctrl, dp = p->dataPort, dd = p->dataDdr, pd = p->portd;
    uint8_t t = p->ticks, fl = p->flags;
    DATA_PORT = dp; DATA_DDR = dd;
    CTRL_PORT = ctrlV;
    PORTD = pd;
    if (t) __asm__ volatile("1: nop\n\tdec %0\n\tbrne 1b" : "+r"(t));   // 4 cycles per tick
    if (fl & F_SAMPLE) {
      if (ns < SAMPLE_MAX) {
        RawSample &r = samples[ns];
        r.g = PING; r.l = PINL; r.b = PINB; r.d = IRQ_PIN_REG;
        sampleStep[ns++] = p - steps;
      }
    }
    p++;
  }
  nSamples = ns;
  uint16_t total = TCNT1;
  TCCR1B = 0;
  overflow = TIFR1 & _BV(TOV1);
  TCCR1A = a1; TCNT1 = c1; TCCR1B = b1;       // restore Arduino's Timer1 setup
  // Back to idle (writes nothing): M2 low, R/W high, /ROMSEL high, data driven high.
  CTRL_PORT = RW_MASK | ROMSEL_N_MASK | ppuBits;
  DATA_PORT = 0xFF; DATA_DDR = 0xFF;
  SREG = sreg;
  return total;
}

// ---- reporting ------------------------------------------------------------
static void printHex(uint32_t v, uint8_t digits) {
  for (int8_t i = digits - 1; i >= 0; i--) Serial.print((v >> (i * 4)) & 0xF, HEX);
}

static void printBin(uint16_t v, uint8_t bits) {
  for (int8_t i = bits - 1; i >= 0; i--) Serial.print((v >> i) & 1);
}

// "out,<hex16>,<bin>" then every named signal.
static void printOutputsWord(uint16_t w) {
  Serial.print(F("out,")); printHex(w, 4); Serial.print(','); printBin(w, OUT_COUNT);
  for (uint8_t i = 0; i < OUT_COUNT; i++) {
    Serial.print(','); Serial.print(OUT_NAMES[i]); Serial.print('=');
    Serial.print((w >> i) & 1);
  }
  Serial.println();
}

static void printOutputs() { printOutputsWord(readOutputs()); }

static void printState() {
  Serial.print(F("bus,data=")); printHex(DATA_PORT, 2);
  Serial.print(F(",M2=")); Serial.print((CTRL_PORT >> BIT_M2) & 1);
  Serial.print(F(",RW=")); Serial.print((CTRL_PORT >> BIT_RW) & 1);
  Serial.print(F(",ROMSEL_N=")); Serial.print((CTRL_PORT >> BIT_ROMSEL_N) & 1);
  Serial.print(F(",A0=")); Serial.print((CTRL_PORT >> BIT_A0) & 1);
  Serial.print(F(",A13=")); Serial.print((CTRL_PORT >> BIT_A13) & 1);
  Serial.print(F(",A14=")); Serial.print((CTRL_PORT >> BIT_A14) & 1);
  Serial.print(F(",PPU_A10=")); Serial.print((CTRL_PORT >> BIT_PPU_A10) & 1);
  Serial.print(F(",PPU_A11=")); Serial.print((CTRL_PORT >> BIT_PPU_A11) & 1);
  Serial.print(F(",PPU_A12=")); Serial.print((PPU_A12_PORT >> BIT_PPU_A12) & 1);
  Serial.print(F(",P19=")); Serial.print(pin19State());
  noInterrupts(); uint16_t c = irqCount; interrupts();
  Serial.print(F(",irq_falls=")); Serial.println(c);
  printOutputs();
}

static void printHelp() {
  Serial.println(F(
    "w ADDR DATA   write mapper reg (hex), e.g. w 8000 06\n"
    "r             read all RAMBO outputs\n"
    "rd ADDR       CPU read cycle (hex); prints outputs sampled with M2 high, /ROMSEL low if >= 8000\n"
    "bus M2 RW ROMSEL_N [A13 A14 A0]  set bus pins at once (0/1), print outputs.\n"
    "              Address defaults to $E000 (A13=1 A14=1 A0=0). M2=1 RW=0 ROMSEL_N=0 is a\n"
    "              register write, so it is refused at any other address.\n"
    "wseq clear|add [M2= RW= ROMSEL= A=hex D=hex|Z A12= T=n S]|list|run [force]\n"
    "              timed pin sequence; unset fields keep the previous step; T in ~250 ns ticks\n"
    "m N           clock M2 N times (idle bus cycles)\n"
    "a N [GAP]     pulse PPU A12 N times, GAP M2 cycles after each (default 0)\n"
    "a12 V         set PPU A12 level (0/1)\n"
    "ppu V10 V11   set PPU A10, A11 levels\n"
    "p19 [0|1|z]   RAMBO pin 19 via D2 + 1k: drive low/high or release; prints state and net level\n"
    "d             dump bus state and outputs\n"
    "c             clear /IRQ falling-edge counter\n"
    "?             this help"));
}

// ---- command interpreter --------------------------------------------------
static bool argHex(const char *s, uint32_t &out) {
  if (!s || !*s) return false;
  char *end; out = strtoul(s, &end, 16);
  return *end == 0;
}
static bool argDec(const char *s, uint32_t &out) {
  if (!s || !*s) return false;
  char *end; out = strtoul(s, &end, 10);
  return *end == 0;
}

static void runCommand(char *line) {
  char *cmd = strtok(line, " \t");
  if (!cmd) return;
  char *a1 = strtok(NULL, " \t");
  char *a2 = strtok(NULL, " \t");
  uint32_t x, y;

  if (!strcmp(cmd, "w")) {
    if (!argHex(a1, x) || !argHex(a2, y) || x < 0x8000 || x > 0xFFFF || y > 0xFF) {
      Serial.println(F("err,usage: w ADDR(8000-FFFF) DATA(00-FF)")); return;
    }
    cpuWrite(x, y);
    Serial.print(F("ok,w,")); printHex(x, 4); Serial.print(','); printHex(y, 2); Serial.println();
  } else if (!strcmp(cmd, "r")) {
    printOutputs();
  } else if (!strcmp(cmd, "rd")) {
    if (!argHex(a1, x) || x > 0xFFFF) { Serial.println(F("err,usage: rd ADDR(0000-FFFF)")); return; }
    uint16_t w = cpuRead(x);
    Serial.print(F("ok,rd,")); printHex(x, 4); Serial.println();
    printOutputsWord(w);
  } else if (!strcmp(cmd, "bus")) {
    char *a3 = strtok(NULL, " \t"), *a4 = strtok(NULL, " \t");
    char *a5 = strtok(NULL, " \t"), *a6 = strtok(NULL, " \t");
    uint32_t v[6] = {0, 0, 0, 1, 1, 0};     // M2 RW ROMSEL_N A13 A14 A0
    const char *args[6] = {a1, a2, a3, a4, a5, a6};
    for (uint8_t i = 0; i < 6; i++) {
      if (i >= 3 && !args[i]) continue;       // address bits are optional
      if (!argDec(args[i], v[i]) || v[i] > 1) {
        Serial.println(F("err,usage: bus M2 RW ROMSEL_N [A13 A14 A0] (0/1 each)")); return;
      }
    }
    bool isWrite = v[0] && !v[1] && !v[2];
    if (isWrite && !(v[3] == 1 && v[4] == 1 && v[5] == 0)) {
      Serial.println(F("err,bus: M2=1 RW=0 ROMSEL_N=0 is a register write; only allowed at $E000")); return;
    }
    uint8_t addrBits = (v[3] ? _BV(BIT_A13) : 0) | (v[4] ? _BV(BIT_A14) : 0) | (v[5] ? _BV(BIT_A0) : 0);
    ctrl(v[0], v[1], v[2], addrBits);
    delayMicroseconds(2);
    Serial.println(F("ok,bus"));
    printOutputs();
  } else if (!strcmp(cmd, "wseq")) {
    if (!a1) { Serial.println(F("err,usage: wseq clear|add ...|list|run [force]")); return; }
    if (!strcmp(a1, "clear")) {
      seqClear();
      Serial.println(F("ok,wseq,clear"));
    } else if (!strcmp(a1, "add")) {
      if (stepCount >= STEP_MAX) { Serial.println(F("err,wseq: step buffer full")); return; }
      SeqState next = seqCur;
      uint8_t ticks = 1; bool sample = false;
      for (char *t = a2; t; t = strtok(NULL, " \t")) {
        if (!seqField(t, next, ticks, sample)) {
          Serial.print(F("err,wseq: bad field ")); Serial.println(t); return;
        }
      }
      seqCur = next;
      uint8_t portd = (PORTD & ~PPU_A12_MASK) | (next.a12 ? PPU_A12_MASK : 0);
      steps[stepCount] = { seqCtrl(next), next.dz ? (uint8_t)0 : next.d, next.dz ? (uint8_t)0 : (uint8_t)0xFF,
                           portd, ticks, (uint8_t)(sample ? F_SAMPLE : 0) };
      stepCount++;
      Serial.print(F("ok,wseq,add,")); Serial.println(stepCount);
    } else if (!strcmp(a1, "list")) {
      for (uint8_t i = 0; i < stepCount; i++) seqPrintStep(i);
      Serial.print(F("ok,wseq,list,")); Serial.println(stepCount);
    } else if (!strcmp(a1, "run")) {
      bool force = a2 && !strcmp(a2, "force");
      if (a2 && !force) { Serial.println(F("err,usage: wseq run [force]")); return; }
      if (!stepCount) { Serial.println(F("err,wseq: empty")); return; }
      if (!force) for (uint8_t i = 0; i < stepCount; i++) if (stepIsRiskyWrite(steps[i])) {
        Serial.print(F("err,wseq: step ")); Serial.print(i);
        Serial.println(F(" is a register write outside $E000; use 'wseq run force'")); return;
      }
      uint8_t n; bool ovf;
      uint16_t cycles = seqRun(n, ovf);
      Serial.print(F("ok,wseq,steps=")); Serial.print(stepCount);
      Serial.print(F(",samples=")); Serial.print(n);
      Serial.print(F(",cycles=")); Serial.print(cycles);
      if (ovf) Serial.print(F(",overflow"));
      Serial.println();
      for (uint8_t k = 0; k < n; k++) {
        Serial.print(F("s,")); Serial.println(sampleStep[k]);
        printOutputsWord(packOutputs(samples[k].g, samples[k].l, samples[k].b, samples[k].d));
      }
    } else {
      Serial.println(F("err,usage: wseq clear|add ...|list|run [force]"));
    }
  } else if (!strcmp(cmd, "m")) {
    if (!argDec(a1, x)) { Serial.println(F("err,usage: m N")); return; }
    clockM2(x);
    Serial.print(F("ok,m,")); Serial.println(x);
  } else if (!strcmp(cmd, "a")) {
    if (!argDec(a1, x) || (a2 && !argDec(a2, y))) { Serial.println(F("err,usage: a N [GAP]")); return; }
    if (!a2) y = 0;
    for (uint32_t i = 0; i < x; i++) { setA12(1); setA12(0); clockM2(y); }
    Serial.print(F("ok,a,")); Serial.print(x); Serial.print(','); Serial.println(y);
  } else if (!strcmp(cmd, "a12")) {
    if (!argDec(a1, x) || x > 1) { Serial.println(F("err,usage: a12 0|1")); return; }
    setA12(x);
    Serial.println(F("ok,a12"));
  } else if (!strcmp(cmd, "ppu")) {
    if (!argDec(a1, x) || !argDec(a2, y) || x > 1 || y > 1) {
      Serial.println(F("err,usage: ppu A10 A11 (0/1 each)")); return;
    }
    ppuBits = (x ? _BV(BIT_PPU_A10) : 0) | (y ? _BV(BIT_PPU_A11) : 0);
    CTRL_PORT = (CTRL_PORT & ~PPU_ADDR_MASK) | ppuBits;
    Serial.println(F("ok,ppu"));
  } else if (!strcmp(cmd, "p19")) {
    if (a1) {
      bool z = (a1[0] == 'z' || a1[0] == 'Z') && !a1[1];
      if (!z && !(argDec(a1, x) && x <= 1)) { Serial.println(F("err,usage: p19 [0|1|z]")); return; }
      setPin19(z ? 2 : x);
    }
    Serial.print(F("ok,p19,")); Serial.print(pin19State());
    Serial.print(F(",net=")); Serial.println((P19_PIN & P19_MASK) ? 1 : 0);
  } else if (!strcmp(cmd, "d")) {
    printState();
  } else if (!strcmp(cmd, "c")) {
    noInterrupts(); irqCount = 0; interrupts();
    Serial.println(F("ok,c"));
  } else if (!strcmp(cmd, "?")) {
    printHelp();
  } else {
    Serial.print(F("err,unknown,")); Serial.println(cmd);
  }
}

void setup() {
  initPins();   // first thing: define every pin
  seqClear();
  Serial.begin(115200);
  attachInterrupt(digitalPinToInterrupt(IRQ_PIN), onIrq, FALLING);
  Serial.println(F("RAMBO-1 jig ready. '?' for help."));
}

void loop() {
  static char buf[96];
  static uint8_t len = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r' || ch == '\n') {
      buf[len] = 0; len = 0;
      runCommand(buf);
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = ch;
    }
  }
}
