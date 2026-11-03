// RAMBO-1 RP2350 jig, milestone M1: safe pin states, power sequencing, USB serial commands (docs/rp2350_adapter_plan.md).
// Rules (CLAUDE.md): every pin has a defined state at the very start of main(); cart power (PWR_EN) before the drivers (OE_EN);
// drivers off before power off. Never connect the adapter to a cart that is in a console.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "pico/bootrom.h"
#include "pins.h"
#include "engine.h"
#include "pico/stdio_usb.h"

#define FW_VERSION "0.4 (M2: PIO engine: load/run/dump)"

static bool power_on = false, oe_on = false;
static uint32_t stim_word = STIM_IDLE;       // what the 17 stimulus pins are currently driven to (bit 0 = D0 = GPIO26)

static void stim_set(uint32_t w) {
    stim_word = w & 0x1FFFFu;
    gpio_put_masked64(((uint64_t)0x1FFFF) << STIM_BASE, ((uint64_t)stim_word) << STIM_BASE);
}

static void stim_write_all(uint32_t v) { stim_set(v); }

static void init_pins_safe(void) {
    // power and driver enables first: low, as the pull-downs on the board hold them
    gpio_init(PIN_PWR_EN); gpio_put(PIN_PWR_EN, 0); gpio_set_dir(PIN_PWR_EN, GPIO_OUT);
    gpio_init(PIN_OE_EN);  gpio_put(PIN_OE_EN, 0);  gpio_set_dir(PIN_OE_EN, GPIO_OUT);
    // stimulus pins: outputs at the idle pattern (all high) so that enabling the drivers causes no edge on the chip
    for (int i = 0; i < STIM_COUNT; i++) { gpio_init(STIM_SIG[i].gpio); gpio_put(STIM_SIG[i].gpio, 1); gpio_set_dir(STIM_SIG[i].gpio, GPIO_OUT); }
    // the chip's outputs: plain inputs, no pulls (the 74LVC541A drives them)
    for (int i = 0; i < OUT_COUNT; i++) { gpio_init(OUT_SIG[i].gpio); gpio_set_dir(OUT_SIG[i].gpio, GPIO_IN); gpio_disable_pulls(OUT_SIG[i].gpio); }
}

static void set_oe(bool on) { gpio_put(PIN_OE_EN, on); oe_on = on; }
static void set_power(bool on) {
    if (!on) set_oe(false);                    // drivers off before power off
    gpio_put(PIN_PWR_EN, on); power_on = on;
}

static bool stim_word_is_idle(void) { return stim_word == STIM_IDLE; }

static void cmd_state(void) {
    printf("power %s, drivers %s\n", power_on ? "ON" : "off", oe_on ? "ON" : "off");
    printf("stimulus (what the RP2350 drives; reaches J2 only when drivers are ON):\n");
    for (int i = 0; i < STIM_COUNT; i++)
        printf("  %-7s GPIO%-2d J2-%-2d = %d\n", STIM_SIG[i].name, STIM_SIG[i].gpio, STIM_SIG[i].j2, gpio_get(STIM_SIG[i].gpio));
    printf("chip outputs (read through the 74LVC541A):\n");
    for (int i = 0; i < OUT_COUNT; i++)
        printf("  %-7s GPIO%-2d J2-%-2d = %d\n", OUT_SIG[i].name, OUT_SIG[i].gpio, OUT_SIG[i].j2, gpio_get(OUT_SIG[i].gpio));
}

static int find_stim(const char *name) {
    for (int i = 0; i < STIM_COUNT; i++) if (strcasecmp(STIM_SIG[i].name, name) == 0) return i;
    return -1;
}

static void out_line(void) {      // one line: CHR A17..A10, PRG A17..A13, /CE, CIRAM A10, /IRQ
    uint64_t g = gpio_get_all64();
    #define G(n) ((int)((g >> (n)) & 1))
    printf("CHR A17..A10 = %d%d%d%d%d%d%d%d  PRG A17..A13 = %d%d%d%d%d  CE %d  CIRAM %d  IRQ %d\n",
           G(21), G(22), G(23), G(12), G(13), G(14), G(43), G(44), G(46), G(47), G(16), G(17), G(18), G(45), G(20), G(19));
    #undef G
}

// A slow CPU write cycle (the same sequence as the Mega jig: M2 low, R/W low, data and address, M2 high, /ROMSEL low, /ROMSEL high, M2 low,
// R/W high). The PPU lines keep their current state. Software timing only (microseconds): not a real-speed cycle.
static void bus_write(unsigned addr, unsigned val) {
    uint32_t w = stim_word;
    w &= ~((1u << S_M2) | (1u << S_RW) | 0xFFu | (1u << S_A0) | (1u << S_A13) | (1u << S_A14));
    w |= (1u << S_ROMSEL) | (val & 0xFFu);
    if (addr & 1) w |= 1u << S_A0;
    if (addr & 0x2000) w |= 1u << S_A13;
    if (addr & 0x4000) w |= 1u << S_A14;
    stim_set(w); sleep_us(5);
    w |= 1u << S_M2; stim_set(w); sleep_us(5);
    w &= ~(1u << S_ROMSEL); stim_set(w); sleep_us(5);
    w |= 1u << S_ROMSEL; stim_set(w); sleep_us(5);
    w &= ~(1u << S_M2); stim_set(w); sleep_us(5);
    w |= 1u << S_RW; stim_set(w); sleep_us(5);
    w |= 0xFFu | (1u << S_M2) | (1u << S_A0) | (1u << S_A13) | (1u << S_A14); stim_set(w);   // back to idle (the PPU lines unchanged)
}

// With the cart's 5 V switched off its supply rail is only a capacitor (the cart's own, plus C6): it falls slowly to about 1 V and the chip keeps its
// registers (found 2026-11-02: a "power off" of a minute left R0-R5 intact). The cart's pull-ups (1 k on D0-D7, 10 k on the control and PPU lines) tie the rail
// to the stimulus lines, so driving every stimulus line LOW with the drivers on discharges the rail through them in about a millisecond. Power must be off.
static void discharge(unsigned ms) {
    set_oe(false);
    stim_set(0);                                // all stimulus lines low, then enable the drivers
    set_oe(true);
    sleep_ms(ms);
    set_oe(false);
    stim_set(STIM_IDLE);
}

static void cold_start(unsigned off_ms) {
    set_power(false);
    discharge(300);
    sleep_ms(off_ms);
    set_power(true);
}

// Binary transfers (the stimulus in, the capture out): raw little-endian 32-bit words over the USB serial port.
static bool read_exact(void *dst, unsigned n) {
    uint8_t *p = (uint8_t *)dst;
    for (unsigned i = 0; i < n; i++) {
        int c = getchar_timeout_us(1000000);
        if (c == PICO_ERROR_TIMEOUT) return false;
        p[i] = (uint8_t)c;
    }
    return true;
}

static void cmd_help(void) {
    printf("commands:\n"
           "  ver                 firmware version\n"
           "  state               power, drivers, every signal level\n"
           "  power on|off        cart 5 V (off also turns the drivers off first)\n"
           "  oe on|off|on-nocart drivers (on needs power on; on-nocart is for checking the board with no cart attached)\n"
           "  idle                all stimulus lines high (the cart's idle state)\n"
           "  set <sig> <0|1>     drive one stimulus line (D0..D7 M2 RW ROMSEL A0 A13 A14 PPUA10 PPUA11 PPUA12)\n"
           "  low <sig>           one line low, all others high (probe the line on J2)\n"
           "  wr <addr> <val>     a slow CPU write cycle, hex (e.g. wr 8000 05): needs power and drivers on\n"
           "  ppu <a12> <a11> <a10>  set the three PPU address lines (0/1)\n"
           "  out                 one line: CHR A17..A10, PRG A17..A13, /CE, CIRAM, /IRQ\n"
           "  discharge [ms]      cart power must be off: drive all stimulus low (drivers on) to discharge the cart's supply rail (default 300 ms)\n"
           "  cold [ms]           a real cold start: power off, discharge, wait [ms] (default 1000), power on (drivers stay off)\n"
           "  load <n>            then n raw 32-bit words (little endian): the stimulus (bit0 = D0 .. bit16 = PPU A12); first and last word must be 0x1FFFF (idle)\n"
           "  run <ncap> [div]    run the stimulus and capture ncap words from the same cycle (div = PIO clock divider, 1 = 150 MHz; default 1)\n"
           "  dump [n]            send the first n captured words (default all): 'data <bytes>' then raw words (bit k = GPIO 16+k)\n"
           "  bootsel             power off and reboot into the UF2 loader (to load new firmware)\n"
           "  help\n");
}

static void handle(char *line) {
    char *argv[4] = {0}; int argc = 0;
    for (char *t = strtok(line, " \t\r\n"); t && argc < 4; t = strtok(NULL, " \t\r\n")) argv[argc++] = t;
    if (!argc) return;
    if (!strcmp(argv[0], "help")) cmd_help();
    else if (!strcmp(argv[0], "ver")) printf("rambo rp2350 jig fw %s\n", FW_VERSION);
    else if (!strcmp(argv[0], "state")) cmd_state();
    else if (!strcmp(argv[0], "power") && argc == 2) {
        if (!strcmp(argv[1], "on")) { set_power(true); printf("power ON (drivers still off)\n"); }
        else if (!strcmp(argv[1], "off")) { set_power(false); printf("drivers off, power off\n"); }
        else printf("? power on|off\n");
    }
    else if (!strcmp(argv[0], "oe") && argc == 2) {
        if (!strcmp(argv[1], "off")) { set_oe(false); printf("drivers off\n"); }
        else if (!strcmp(argv[1], "on")) {
            if (!power_on) printf("refused: power the cart first (power on), or use on-nocart with no cart attached\n");
            else { set_oe(true); printf("drivers ON\n"); }
        }
        else if (!strcmp(argv[1], "on-nocart")) {
            if (power_on) printf("refused: power is on; use 'oe on'\n");
            else { set_oe(true); printf("drivers ON, cart power off: attach NO cart\n"); }
        }
        else printf("? oe on|off|on-nocart\n");
    }
    else if (!strcmp(argv[0], "idle")) { stim_write_all(STIM_IDLE); printf("stimulus idle (all high)\n"); }
    else if (!strcmp(argv[0], "set") && argc == 3) {
        int i = find_stim(argv[1]);
        if (i < 0) printf("? unknown stimulus line '%s'\n", argv[1]);
        else { uint32_t w = stim_word & ~(1u << i); if (atoi(argv[2]) != 0) w |= 1u << i; stim_set(w); printf("%s = %d\n", STIM_SIG[i].name, atoi(argv[2]) != 0); }
    }
    else if (!strcmp(argv[0], "low") && argc == 2) {
        int i = find_stim(argv[1]);
        if (i < 0) printf("? unknown stimulus line '%s'\n", argv[1]);
        else { stim_write_all(STIM_IDLE & ~(1u << i)); printf("%s (J2-%d) low, others high\n", STIM_SIG[i].name, STIM_SIG[i].j2); }
    }
    else if (!strcmp(argv[0], "wr") && argc == 3) {
        if (!power_on || !oe_on) printf("refused: power and drivers must be on\n");
        else { bus_write((unsigned)strtoul(argv[1], 0, 16), (unsigned)strtoul(argv[2], 0, 16)); printf("wrote %s to %s\n", argv[2], argv[1]); }
    }
    else if (!strcmp(argv[0], "ppu") && argc == 4) {
        uint32_t w = stim_word & ~((1u << S_PPU_A12) | (1u << S_PPU_A11) | (1u << S_PPU_A10));
        if (atoi(argv[1])) w |= 1u << S_PPU_A12;
        if (atoi(argv[2])) w |= 1u << S_PPU_A11;
        if (atoi(argv[3])) w |= 1u << S_PPU_A10;
        stim_set(w); printf("PPU A12 A11 A10 = %d %d %d\n", !!atoi(argv[1]), !!atoi(argv[2]), !!atoi(argv[3]));
    }
    else if (!strcmp(argv[0], "discharge")) {
        if (power_on) printf("refused: cart power is on (power off first)\n");
        else { unsigned ms = argc > 1 ? (unsigned)atoi(argv[1]) : 300; discharge(ms ? ms : 300); printf("discharged for %u ms; drivers off\n", ms ? ms : 300); }
    }
    else if (!strcmp(argv[0], "cold")) {
        unsigned ms = argc > 1 ? (unsigned)atoi(argv[1]) : 1000; cold_start(ms); printf("cold start done (off %u ms); power ON, drivers off\n", ms);
    }
    else if (!strcmp(argv[0], "load") && argc == 2) {
        unsigned n = (unsigned)strtoul(argv[1], 0, 0);
        if (n == 0 || n > ENG_MAX_STIM) printf("refused: 1..%u words\n", (unsigned)ENG_MAX_STIM);
        else {
            printf("ready %u\n", n); stdio_flush();
            if (read_exact(eng_stim, n * 4)) { eng_nstim = n; printf("loaded %u words\n", n); }
            else { eng_nstim = 0; printf("load timed out\n"); }
        }
    }
    else if (!strcmp(argv[0], "run") && argc >= 2) {
        unsigned ncap = (unsigned)strtoul(argv[1], 0, 0); float div = argc > 2 ? (float)atof(argv[2]) : 1.0f;
        if (!stim_word_is_idle()) printf("note: stimulus lines are not idle before the run\n");
        eng_result_t r = engine_run(ncap, div);
        printf("%s: stim %u words, captured %u words, div %.3f, fdebug 0x%08lX %s\n", r.ok ? "run ok" : "run FAILED", eng_nstim, eng_ncap, (double)div, (unsigned long)r.fdebug, r.why);
        stim_word = STIM_IDLE;
    }
    else if (!strcmp(argv[0], "dump")) {
        unsigned n = argc > 1 ? (unsigned)strtoul(argv[1], 0, 0) : eng_ncap; if (n > eng_ncap) n = eng_ncap;
        printf("data %u\n", n * 4); stdio_flush();
        for (unsigned off = 0; off < n * 4; off += 2048) {
            unsigned len = n * 4 - off; if (len > 2048) len = 2048;
            stdio_put_string((const char *)eng_cap + off, (int)len, false, false);
        }
        stdio_flush(); printf("\nend\n");
    }
    else if (!strcmp(argv[0], "out")) out_line();
    else if (!strcmp(argv[0], "bootsel")) { printf("power off, rebooting into the UF2 loader\n"); sleep_ms(50); set_power(false); reset_usb_boot(0, 0); }
    else printf("? unknown command (help)\n");
}

int main(void) {
    init_pins_safe();                          // before anything else
    stdio_init_all();
    stdio_set_translate_crlf(&stdio_usb, false);   // binary transfers: no CR/LF translation
    char line[64]; int n = 0;
    printf("\nrambo rp2350 jig fw %s: power off, drivers off. 'help' for commands.\n> ", FW_VERSION);
    for (;;) {
        int c = getchar_timeout_us(100000);
        if (c == PICO_ERROR_TIMEOUT) continue;
        if (c == '\r' || c == '\n') {
            line[n] = 0; putchar('\n');
            if (n) handle(line);
            n = 0; printf("> ");
        } else if (c == 8 || c == 127) { if (n) { n--; printf("\b \b"); } }
        else if (n < (int)sizeof line - 1) { line[n++] = (char)c; putchar(c); }
    }
}
