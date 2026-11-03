// RAMBO-1 jig PIO engine: synchronised stimulus and capture (see engine.pio).
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "engine.pio.h"
#include "engine.h"
#include "pins.h"

uint32_t eng_stim[ENG_MAX_STIM];
uint32_t eng_cap[ENG_MAX_CAP];
unsigned eng_nstim = 0, eng_ncap = 0;

#define ENG_PIO   pio0
#define SM_STIM   0
#define SM_CAP    1
#define CAP_BASE  16                               // the capture window is GPIO16..47 (the PIO block's GPIO base)

static bool inited = false;
static int stim_off, cap_off;
static int dma_tx = -1, dma_rx = -1;

static void engine_init(void) {
    if (inited) return;
    pio_set_gpio_base(ENG_PIO, CAP_BASE);
    stim_off = pio_add_program(ENG_PIO, &stim_raw_program);
    cap_off  = pio_add_program(ENG_PIO, &cap_raw_program);
    pio_sm_claim(ENG_PIO, SM_STIM);
    pio_sm_claim(ENG_PIO, SM_CAP);
    dma_tx = dma_claim_unused_channel(true);
    dma_rx = dma_claim_unused_channel(true);
    inited = true;
}

eng_result_t engine_run(unsigned ncap, float div) {
    eng_result_t r = { false, 0, "" };
    engine_init();
    if (eng_nstim == 0 || eng_nstim > ENG_MAX_STIM) { r.why = "no stimulus loaded"; return r; }
    if (ncap == 0 || ncap > ENG_MAX_CAP) { r.why = "capture length out of range"; return r; }
    if (div < 1.0f) { r.why = "clock divider below 1"; return r; }
    if ((eng_stim[eng_nstim - 1] & 0x1FFFFu) != STIM_IDLE || (eng_stim[0] & 0x1FFFFu) != STIM_IDLE) { r.why = "the stimulus must start and end at the idle word 0x1FFFF"; return r; }

    PIO pio = ENG_PIO;
    pio_sm_set_enabled(pio, SM_STIM, false);
    pio_sm_set_enabled(pio, SM_CAP, false);

    // stimulus state machine
    pio_sm_config c = stim_raw_program_get_default_config(stim_off);
    sm_config_set_out_pins(&c, STIM_BASE, STIM_COUNT);
    sm_config_set_out_shift(&c, true, true, STIM_COUNT);   // shift right, autopull, threshold 17: one word per instruction
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
    sm_config_set_clkdiv(&c, div);
    pio_sm_init(pio, SM_STIM, stim_off, &c);
    // capture state machine
    pio_sm_config d = cap_raw_program_get_default_config(cap_off);
    sm_config_set_in_pin_base(&d, CAP_BASE);
    sm_config_set_in_pin_count(&d, 32);
    sm_config_set_in_shift(&d, true, true, 32);
    sm_config_set_fifo_join(&d, PIO_FIFO_JOIN_RX);
    sm_config_set_clkdiv(&d, div);
    pio_sm_init(pio, SM_CAP, cap_off, &d);
    // read the pads without the two-cycle input synchroniser (the same latency on every channel)
    pio_set_input_sync_bypass_with_mask64(pio, 0xFFFFFFFFull << CAP_BASE, 0xFFFFFFFFull << CAP_BASE);

    // The stimulus pins must hold the idle pattern when the PIO takes them over (no glitch on M2, R/W, /ROMSEL): set the PIO output
    // register and the direction first, then switch the pin function.
    uint64_t pinmask = ((uint64_t)0x1FFFF) << STIM_BASE;
    pio_sm_set_pins_with_mask64(pio, SM_STIM, ((uint64_t)STIM_IDLE) << STIM_BASE, pinmask);
    pio_sm_set_pindirs_with_mask64(pio, SM_STIM, pinmask, pinmask);
    for (int i = 0; i < STIM_COUNT; i++) pio_gpio_init(pio, STIM_BASE + i);

    pio->fdebug = 0xFFFFFFFFu;                      // clear the sticky stall/overflow flags
    // DMA: stimulus buffer -> TX FIFO, RX FIFO -> capture buffer
    dma_channel_config tc = dma_channel_get_default_config(dma_tx);
    channel_config_set_transfer_data_size(&tc, DMA_SIZE_32);
    channel_config_set_read_increment(&tc, true);
    channel_config_set_write_increment(&tc, false);
    channel_config_set_dreq(&tc, pio_get_dreq(pio, SM_STIM, true));
    dma_channel_configure(dma_tx, &tc, &pio->txf[SM_STIM], eng_stim, eng_nstim, false);
    dma_channel_config rc = dma_channel_get_default_config(dma_rx);
    channel_config_set_transfer_data_size(&rc, DMA_SIZE_32);
    channel_config_set_read_increment(&rc, false);
    channel_config_set_write_increment(&rc, true);
    channel_config_set_dreq(&rc, pio_get_dreq(pio, SM_CAP, false));
    dma_channel_configure(dma_rx, &rc, eng_cap, &pio->rxf[SM_CAP], ncap, false);
    dma_start_channel_mask((1u << dma_tx) | (1u << dma_rx));
    sleep_us(50);                                    // the TX FIFO fills before the state machines start

    pio_enable_sm_mask_in_sync(pio, (1u << SM_STIM) | (1u << SM_CAP));   // both start in the same cycle

    absolute_time_t t_end = make_timeout_time_ms(2000);
    while (dma_channel_is_busy(dma_rx) && !time_reached(t_end)) tight_loop_contents();
    bool timeout = dma_channel_is_busy(dma_rx);
    pio_set_sm_mask_enabled(pio, (1u << SM_STIM) | (1u << SM_CAP), false);
    r.fdebug = pio->fdebug;
    bool tx_unfinished = dma_channel_is_busy(dma_tx);
    dma_channel_abort(dma_tx);
    dma_channel_abort(dma_rx);

    // give the pins back to the CPU at the idle pattern
    gpio_put_masked64(pinmask, ((uint64_t)STIM_IDLE) << STIM_BASE);
    for (int i = 0; i < STIM_COUNT; i++) gpio_set_function(STIM_BASE + i, GPIO_FUNC_SIO);
    gpio_set_dir_out_masked64(pinmask);
    pio_sm_set_consecutive_pindirs(pio, SM_STIM, STIM_BASE, STIM_COUNT, false);

    eng_ncap = ncap;
    r.ok = !timeout && !tx_unfinished;
    r.why = timeout ? "the capture did not complete (timeout)" : tx_unfinished ? "the stimulus was longer than the capture" : "";
    return r;
}
