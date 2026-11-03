; RAMBO-1 timing probe: not a test. It repeats one bus pattern forever so that a logic analyser on the cart's J2 header always catches
; the event it is looking for (docs/logic_analyzer_guide.md, section 10). Five phases, chosen by the controller button held while the
; console is reset (or powered on):
;     none or A  1 DATA WRITES      $A000 written with alternating data, CIRAM A10 follows
;     B          2 CONTROL WRITES   $8000 written with the C bit toggling (A0 = 0), CHR outputs switch between R0 and R2
;     SELECT     3 IRQ ACK LOOP     CPU-cycle interrupt every 164 cycles, the handler writes $E000 and $E001
;     START      4 PRG BANK OUTPUTS reads of $8000, $A000 and $C000 in a loop: CPU A13/A14 to the PRG A13-A17 outputs
;     UP         5 CHR OUTPUTS      PPUADDR cycling through four windows: PPU A10-A12 to the CHR A10-A17 and CIRAM A10 outputs
;     DOWN       6 BANK DATA WRITES $8001 written with alternating data, CHR A11-A17 follow R0 (same leads as phase 2)
;     LEFT       7 ENABLE RACE      $E001 written at cycle 18..26 after $C001 (CPU mode, latch 4: first expiry at cycle 22)
;     RIGHT      8 DISABLE RACE     $E000 written at cycle 18..26 after $C001, with the interrupt already enabled
;     A + UP     9 A12 ENABLE RACE  A12 mode with rendering on; a 228-cycle loop drifts 2/3 cycle per iteration against the PPU's line pairs, so an $E001
;                                   write sweeps across the clocking M2 fall of a counted A12 pulse
;     A + DOWN  10 A12 DISABLE RACE the same with $E001 early and $E000 swept
;     B + UP    11 GAP SWEEP L=0    A12 mode, rendering off (no A12 pulses at all): $E000, $C001 and $E001 written with gaps g1 (E000 to C001) and g2 (C001 to E001)
;                                   from a grid; does /IRQ go low (finding F-073)?
;     B + DOWN  12 GAP SWEEP L=3    the same with latch 3
;     START + UP   13 PHASE 10 LOOP, rendering on, both tables at $0000 (no A12 pulses)
;     START + DOWN 14 PHASE 10 LOOP, rendering off
;     SELECT + UP  15 PHASE 10 LOOP, rendering off, 231 cycles per iteration (the alignment to a 4-cycle prescaler steps by 3 each time)
;     START + LEFT  18 FREE-RUNNING COUNTER, latch 0: A12 mode, $C001 written once, then $E000/$E001 every 114 cycles (about one line); does /IRQ expire again after the first expiry?
;     START + RIGHT 19 the same with latch 1 (control: every second pulse)
;     SELECT + START 17 the phase 14 loop with the original dex/bne delay loop (page-safe: checked at link time) instead of straight-line padding
;     SELECT + DOWN 16 PERIOD SCAN: the phase 10 loop, rendering off, 40 iterations at each period 224, 225, ... 236 cycles, then round again
; The chosen phase is shown on the screen for three seconds with the J2 pins to connect; then the screen goes blank (rendering off, so the
; PPU address bus is quiet) and the loop runs. Docs: docs/timing_measurements.md.
.include "common/vars.inc"

CUSTOM_IRQ = 1
CUSTOM_MAIN = 1

rom_title: .asciiz "RAMBO-1 TIMING PROBE"
rom_note:  .asciiz ""

.zeropage
phase:  .res 1                  ; 0..18
pad:    .res 1                  ; controller 1: A = bit 7, B = bit 6, SELECT = bit 5, START = bit 4, UP = bit 3
.code

irq:    sta MAP_IRQOFF          ; phase 3 only: acknowledge and enable again (A does not matter)
        sta MAP_IRQON
        rti

.macro SAY label                ; print a zero-terminated string into the text buffer (lib.s defines PRINT after the code)
        lda #<label
        sta ptr
        lda #>label
        sta ptr+1
        jsr print_str
.endmacro

.macro REGW idx, val            ; $8000 index (K = 0), then $8001 data
        lda #idx
        sta MAP_BANKSEL
        lda #val
        sta MAP_BANKDATA
.endmacro

.macro REGW1K idx, val          ; the same with K = 1 (1 KB CHR windows)
        lda #(idx | $20)
        sta MAP_BANKSEL
        lda #val
        sta MAP_BANKDATA
.endmacro

.macro PPUADDR_ZERO
        bit PPUSTATUS
        lda #0
        sta PPUADDR
        sta PPUADDR
.endmacro

main:
        lda #0
        sta RESULT_STATUS       ; green screen
        jsr read_pad
        SAY rom_title
        jsr newline
        ldx phase
        lda info_lo,x
        sta ptr
        lda info_hi,x
        sta ptr+1
        jsr print_str
        jsr newline
        SAY s_foot
        lda #0
        ldy #0
        sta (txtp),y            ; terminate the text
        jsr draw_screen
        lda #180
        jsr wait_frames         ; three seconds on the screen
        lda #0
        sta PPUMASK             ; rendering off: the PPU address bus now only shows what the ROM writes
        sta PPUCTRL
        sei
        sta MAP_IRQOFF          ; release the power-on /IRQ
        lda phase
        asl a
        tax
        lda jtab,x
        sta jvec
        lda jtab+1,x
        sta jvec+1
        jmp (jvec)

read_pad:                       ; button -> phase
        lda #1
        sta JOY1
        lda #0
        sta JOY1
        sta pad
        sta phase
        ldx #8
@r:     lda JOY1
        lsr a
        rol pad
        dex
        bne @r
        lda pad
        and #$88                ; A + UP
        cmp #$88
        bne @ad
        lda #8
        sta phase
        rts
@ad:    lda pad
        and #$84                ; A + DOWN
        cmp #$84
        bne @b
        lda #9
        sta phase
        rts
@b:     lda pad
        and #$12                ; START + LEFT
        cmp #$12
        bne @sl
        lda #17
        sta phase
        rts
@sl:    lda pad
        and #$11                ; START + RIGHT
        cmp #$11
        bne @sr
        lda #18
        sta phase
        rts
@sr:    lda pad
        and #$30                ; SELECT + START
        cmp #$30
        bne @ss
        lda #16
        sta phase
        rts
@ss:    lda pad
        and #$24                ; SELECT + DOWN
        cmp #$24
        bne @su0
        lda #15
        sta phase
        rts
@su0:   lda pad
        and #$28                ; SELECT + UP
        cmp #$28
        bne @su
        lda #14
        sta phase
        rts
@su:    lda pad
        and #$18                ; START + UP
        cmp #$18
        bne @sd
        lda #12
        sta phase
        rts
@sd:    lda pad
        and #$14                ; START + DOWN
        cmp #$14
        bne @b0
        lda #13
        sta phase
        rts
@b0:    lda pad
        and #$48                ; B + UP
        cmp #$48
        bne @bd
        lda #10
        sta phase
        rts
@bd:    lda pad
        and #$44                ; B + DOWN
        cmp #$44
        bne @b1
        lda #11
        sta phase
        rts
@b1:    lda pad
        and #$40                ; B
        beq @sel
        lda #1
        sta phase
        rts
@sel:   lda pad
        and #$20
        beq @st
        lda #2
        sta phase
        rts
@st:    lda pad
        and #$10
        beq @up
        lda #3
        sta phase
        rts
@up:    lda pad
        and #$08
        beq @d
        lda #4
        sta phase
        rts
@d:     lda pad
        and #$04                ; DOWN
        beq @lf
        lda #5
        sta phase
        rts
@lf:    lda pad
        and #$02                ; LEFT
        beq @rt
        lda #6
        sta phase
        rts
@rt:    lda pad
        and #$01                ; RIGHT
        beq @x
        lda #7
        sta phase
@x:     rts

jtab:   .addr p_data, p_ctrl, p_irq, p_prg, p_chr, p_bank, p_race1, p_race2, p_a12a, p_a12b, p_sw0, p_sw3, p_v1, p_v2, p_v3, p_scan, p_old, p_f0, p_f1
info_lo: .byte <i1, <i2, <i3, <i4, <i5, <i6, <i7, <i8, <i9, <i10, <i11, <i12, <i13, <i14, <i15, <i16, <i17, <i18, <i19
info_hi: .byte >i1, >i2, >i3, >i4, >i5, >i6, >i7, >i8, >i9, >i10, >i11, >i12, >i13, >i14, >i15, >i16, >i17, >i18, >i19

; phase 1: mirroring register written with $00 and $01; PPU address $2400 (A10 = 1, A11 = 0), so CIRAM A10 follows the register
p_data: bit PPUSTATUS
        lda #$24
        sta PPUADDR
        lda #$00
        sta PPUADDR
@l:     lda #$00
        sta MAP_MIRROR
        lda #$01
        sta MAP_MIRROR
        jmp @l

; phase 2: R0 = $FE, R2 = 0; the C bit swaps the 4 KB halves, so window 0 shows R2 or R0
p_ctrl: REGW 0, $FE
        REGW 2, $00
        PPUADDR_ZERO
@l:     lda #$80
        sta MAP_BANKSEL
        lda #$00
        sta MAP_BANKSEL
        jmp @l

; phase 3: CPU-cycle mode, latch 40: an expiry 4 x 41 = 164 cycles apart; the handler runs in about 21 cycles
p_irq:  lda #40
        sta MAP_IRQLATCH
        lda #1
        sta MAP_IRQMODE
        sta MAP_IRQON
        cli
@l:     jmp @l

; phase 4: R6 = $00, R7 = $15, RF = $0A: the PRG A13-A17 outputs differ in the three windows
p_prg:  REGW 6, $00
        REGW 7, $15
        REGW 15, $0A
@l:     lda $8000
        lda $A000
        lda $C000
        jmp @l

; phase 5: K = 1; windows $0000, $0400, $0800 hold banks 0, 1, 2 and $1000 holds $FF, so CHR A10, A11 and A12-A17 follow PPU A10-A12
p_chr:  REGW1K 0, $00
        REGW1K 8, $01
        REGW1K 1, $02
        REGW1K 9, $03
        REGW1K 2, $FF
        REGW1K 3, $FF
        REGW1K 4, $FF
        REGW1K 5, $FF
        bit PPUSTATUS
@l:     lda #$00
        sta PPUADDR
        sta PPUADDR
        lda #$04
        sta PPUADDR
        lda #$00
        sta PPUADDR
        lda #$08
        sta PPUADDR
        lda #$00
        sta PPUADDR
        lda #$10
        sta PPUADDR
        lda #$00
        sta PPUADDR
        jmp @l

; phase 6: R0 data written with $FE and $00 (PPU address 0): CHR A11-A17 follow R0 bits 1-7
p_bank: PPUADDR_ZERO
        lda #0
        sta MAP_BANKSEL         ; index 0, K = 0, C = 0
@l:     lda #$FE
        sta MAP_BANKDATA
        lda #$00
        sta MAP_BANKDATA
        jmp @l

; phases 7 and 8: the sub-cycle question. CPU-cycle mode, latch 4: after the $C001 write cycle (cycle 0) the first expiry is at cycle 4 x 5 + 2 = 22, the next at 42.
; Cycles are counted so that the write cycle of the $E001 (phase 7) or $E000 (phase 8) lands on cycle j = 18 .. 26 after $C001. PAD burns exactly 3 x n3 + 2 x n2 cycles.
.macro PAD n3, n2
        .repeat n3
        bit $00                 ; zero page read, 3 cycles, leaves A alone (lda $00 loaded a stray RAM byte into A)
        .endrepeat
        .repeat n2
        nop                     ; 2 cycles
        .endrepeat
.endmacro

.macro PADG n                   ; burn exactly n cycles (n = 0, 2, 3, 4, ...)
        .if (n) & 1
        bit $00                 ; 3 cycles, leaves A alone
        .endif
        .repeat ((n) - ((n) & 1) * 3) / 2
        nop
        .endrepeat
.endmacro

.macro WAITACK                  ; about 31 cycles, then acknowledge and disable
        ldx #6
        .local w
w:      dex
        bne w
        sta MAP_IRQOFF
.endmacro

; phase 7: disabled before $C001; $E001 written in cycle j (the write cycle is the last of the 4 cycles of the STA). pad = j - 4
.macro RACE1 n3, n2
        sta MAP_IRQOFF          ; disable, release
        lda #4
        sta MAP_IRQLATCH
        lda #1
        sta MAP_IRQMODE         ; cycle 0
        PAD n3, n2
        sta MAP_IRQON           ; cycle 4 + pad
        WAITACK
        nop
        nop
        nop
.endmacro

; phase 8: $E001 early (cycle 8), $E000 in cycle j. pad = j - 12
.macro RACE2 n3, n2
        sta MAP_IRQOFF
        lda #4
        sta MAP_IRQLATCH
        lda #1
        sta MAP_IRQMODE         ; cycle 0
        nop
        nop
        sta MAP_IRQON           ; cycle 8
        PAD n3, n2
        sta MAP_IRQOFF          ; cycle 12 + pad
        WAITACK
        nop
        nop
        nop
.endmacro

p_race1:
race1_top:
        RACE1 0, 7              ; j = 18
        RACE1 1, 6              ; 19
        RACE1 0, 8              ; 20
        RACE1 1, 7              ; 21
        RACE1 0, 9              ; 22
        RACE1 1, 8              ; 23
        RACE1 0, 10             ; 24
        RACE1 1, 9              ; 25
        RACE1 0, 11             ; 26
        jmp race1_top

p_race2:
race2_top:
        RACE2 0, 3              ; j = 18
        RACE2 1, 2              ; 19
        RACE2 0, 4              ; 20
        RACE2 1, 3              ; 21
        RACE2 0, 5              ; 22
        RACE2 1, 4              ; 23
        RACE2 0, 6              ; 24
        RACE2 1, 5              ; 25
        RACE2 0, 7              ; 26
        jmp race2_top

; phases 9 and 10: the same question for an A12-mode clock. Rendering is on (sprites at $1000, background at $0000, NMI off) so the PPU gives one counted A12 pulse per line,
; 113.667 CPU cycles apart. The loop below takes exactly 228 cycles, so each iteration sits 2/3 cycle later against the pulses than the one before: the $E00x write at
; cycle 177 of the iteration (170 after the $C001 write) sweeps across the M2 fall that clocks the counter. Latch 0: the first counted pulse after $C001 is swallowed,
; the second expires. The capture analyser (tools/la_p9_analysis.py) replays the captured bus through the reference model and compares /IRQ.
.macro A12SETUP
        lda #0
        sta MAP_IRQLATCH        ; latch 0
        lda #$08
        sta PPUCTRL             ; sprites at $1000, background at $0000, no NMI
        lda #$18
        sta PPUMASK             ; background and sprites on
        lda #0
.endmacro

p_a12a:
        A12SETUP
a12a_top:
        sta MAP_IRQOFF          ; cycle 3: acknowledge and disable
        sta MAP_IRQMODE         ; cycle 7: $C001, A12 mode, restart
        PADG 166
        sta MAP_IRQON           ; cycle 177: $E001, 170 cycles after $C001
        PAD 15, 1               ; 47 cycles
        jmp a12a_top            ; 228 in all

p_a12b:
        A12SETUP
a12b_top:
        sta MAP_IRQOFF          ; cycle 3
        sta MAP_IRQMODE         ; cycle 7
        sta MAP_IRQON           ; cycle 11: enabled early
        PADG 162
        sta MAP_IRQOFF          ; cycle 177: $E000
        PAD 15, 1
        jmp a12b_top

; phases 11 and 12: no PPU activity (rendering off, A12 low), A12 mode, latch 0 or 3. One block: $E000, then g1 cycles later $C001 (data 0, from Y), then g2 cycles later $E001, then
; 61 cycles of waiting, an acknowledging $E000 and 41 idle cycles. The grid of (g1, g2) is unrolled; does /IRQ go low although no A12 pulse arrives (F-073)?
.macro SW g1, g2
        sta MAP_IRQOFF          ; $E000
        PADG g1 - 4
        sty MAP_IRQMODE         ; $C001, A12 mode, g1 cycles after the $E000
        PADG g2 - 4
        sta MAP_IRQON           ; $E001, g2 cycles after the $C001
        ldx #12
        .local w
w:      dex
        bne w                   ; 61 cycles
        sta MAP_IRQOFF          ; acknowledge
        ldx #8
        .local v
v:      dex
        bne v                   ; 41 cycles idle
.endmacro

.macro SWROW g1
        SW g1, 4
        SW g1, 9
        SW g1, 24
        SW g1, 44
.endmacro

.macro SWSET
        SWROW 4
        SWROW 8
        SWROW 24
.endmacro

p_sw0:  lda #0
        sta MAP_IRQLATCH
        ldy #0
        lda #0
sw0_top:
        SWSET
        jmp sw0_top

p_sw3 = p_sw0            ; phase 12 (latch 3) was dropped to make room: it runs phase 11

; phases 13 and 14: the phase 10 loop ($E000, $C001, $E001 at 3, 7, 11 and $E000 at 177, 228 cycles in all) with the PPU changed, to find what phase 10's early /IRQ depends on (F-073).
.macro P10LOOP top
top:    sta MAP_IRQOFF
        sta MAP_IRQMODE
        sta MAP_IRQON
        PADG 162
        sta MAP_IRQOFF
        PAD 15, 1
        jmp top
.endmacro

p_v1:   lda #0
        sta MAP_IRQLATCH
        lda #$00
        sta PPUCTRL             ; both pattern tables at $0000: no A12 pulses
        lda #$18
        sta PPUMASK             ; rendering on
        lda #0
        P10LOOP v1_top

p_v2:   lda #0
        sta MAP_IRQLATCH
        sta PPUCTRL
        sta PPUMASK             ; rendering off
        P10LOOP v2_top

p_v3:   lda #0
        sta MAP_IRQLATCH
        sta PPUCTRL
        sta PPUMASK
v3_top: sta MAP_IRQOFF
        sta MAP_IRQMODE
        sta MAP_IRQON
        PADG 162
        sta MAP_IRQOFF
        PAD 16, 1               ; 50 cycles: 231 in all
        jmp v3_top

; phase 16: the phase 10 loop ($E000 at 3, $C001 at 7, $E001 at 11, $E000 at 177) run for 40 iterations at each period P = 224 ... 236, then the next period, and round again.
; Y counts the iterations (dey, beq not taken, jmp = 7 cycles in the period). The tail pad is P - 185 cycles. No loop in the exact-timing phases uses a taken branch, so a layout change
; cannot add the extra cycle a branch across a page boundary costs.
.macro SCANSEG top, per
        ldy #40
top:    sta MAP_IRQOFF
        sta MAP_IRQMODE
        sta MAP_IRQON
        PADG 162
        sta MAP_IRQOFF          ; cycle 177
        PADG per - 185
        dey
        .local out
        beq out                 ; not taken except at the end of the segment
        jmp top                 ; 2 + 2 + 3 cycles: no page-crossing branch in the loop
out:
.endmacro

p_scan: lda #0
        sta MAP_IRQLATCH
        sta PPUCTRL
        sta PPUMASK
scan_all:
        SCANSEG sg0, 224
        SCANSEG sg1, 225
        SCANSEG sg2, 226
        SCANSEG sg3, 227
        SCANSEG sg4, 228
        SCANSEG sg5, 229
        SCANSEG sg6, 230
        SCANSEG sg7, 231
        SCANSEG sg8, 232
        SCANSEG sg9, 233
        SCANSEG sg10, 234
        SCANSEG sg11, 235
        SCANSEG sg12, 236
        jmp scan_all

; phase 17: the phase 14 loop as first built: the 162-cycle delay is a dex/bne loop (ldx #31, 156 cycles, then three nops), not straight-line padding. The loop must not straddle a page
; (a taken branch across a page costs a cycle); the .assert fails the link if it does.
p_old:  lda #0
        sta MAP_IRQLATCH
        sta PPUCTRL
        sta PPUMASK
old_top:
        sta MAP_IRQOFF
        sta MAP_IRQMODE
        sta MAP_IRQON
        ldx #31
old_d:  dex
        bne old_d               ; 156 cycles
        nop
        nop
        nop
        .assert .hibyte(old_d) = .hibyte(old_d + 3), error, "phase 17 delay loop crosses a page"
        sta MAP_IRQOFF
        PAD 15, 1
        jmp old_top

; phases 18 and 19: a counter that runs free. A12 mode with rendering on (sprites at $1000): $C001 is written once (data 0 from Y, with rendering off and A12 low so the filter is full), then the loop
; writes $E000 and $E001 every 114 cycles (a scanline is 113.667), so every counted pulse falls in its own acknowledge window. Latch 0 (phase 18): the model says one expiry, after $C001; the
; old model said one per pulse. Latch 1 (phase 19, control): one expiry every second pulse (F-059).
.macro FREE lat, top
        ldy #0
        lda #$08
        sta PPUCTRL             ; sprites at $1000
        lda #0
        sta PPUMASK             ; rendering off while the counter is set up (A12 stays low)
        sta MAP_IRQOFF
        lda #lat
        sta MAP_IRQLATCH
        PADG 60                 ; A12 low for well over 16 falls: the filter is full
        sty MAP_IRQMODE         ; $C001, A12 mode (data 0)
        lda #$18
        sta PPUMASK             ; rendering on: counted pulses start
        sta MAP_IRQON
top:    sta MAP_IRQOFF
        sta MAP_IRQON
        PADG 103                ; 4 + 4 + 103 + 3 = 114 cycles
        jmp top
.endmacro

p_f0:   FREE 0, f0_top
p_f1:   FREE 1, f1_top

i1:     .byte "PHASE 1: DATA WRITES $A000", 10, 10
        .byte "CH1 M2 12     CH2 D0 3", 10
        .byte "CH3 CE 28     CH6 CIRAM 39", 10
        .byte "CH7 R/W 13    CH8 ROMSEL 14", 10
        .byte "(CH4 CH5 NOT USED)", 0
i2:     .byte "PHASE 2: CONTROL WRITES $8000", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 D7 10", 10
        .byte "CH5 A0 15     CH6 CHR11 31", 10
        .byte "CH7 CHR17 37  CH8 CE 28", 0
i3:     .byte "PHASE 3: IRQ ACK LOOP", 10, 10
        .byte "CH1 M2 12     CH2 CE 28", 10
        .byte "CH3 IRQ 40    CH7 R/W 13", 10
        .byte "CH8 ROMSEL 14", 10
        .byte "(CH4 CH5 CH6 NOT USED)", 0
i4:     .byte "PHASE 4: PRG BANK OUTPUTS", 10, 10
        .byte "CH1 M2 12     CH2 A14 17", 10
        .byte "CH3 PRG13 23  CH4 PRG14 24", 10
        .byte "CH5 A13 16    CH6 PRG15 25", 10
        .byte "CH7 PRG16 26  CH8 PRG17 27", 0
i5:     .byte "PHASE 5: CHR OUTPUTS", 10, 10
        .byte "CH2 PPU12 21  CH4 PPU10 19", 10
        .byte "CH5 PPU11 20  CH6 CIRAM 39", 10
        .byte "CH3 CHR10 30  CH7 CHR11 31", 10
        .byte "CH8 CHR17 37  (CH1 M2 12)", 0
i6:     .byte "PHASE 6: BANK DATA $8001", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 D7 10", 10
        .byte "CH7 CHR11 31  CH8 CHR17 37", 0
i7:     .byte "PHASE 7: ENABLE RACE", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i8:     .byte "PHASE 8: DISABLE RACE", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i9:     .byte "PHASE 9: A12 ENABLE RACE", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 10
        .byte "CH7 PPU12 21", 0
i10:    .byte "PHASE 10: A12 DISABLE RACE", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 10
        .byte "CH7 PPU12 21", 0
i11:    .byte "PHASE 11: GAP SWEEP L=0", 10, 10
        .byte "NO A12 PULSES, RENDER OFF", 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i12:    .byte "PHASE 12: = PHASE 11 (L=0)", 10, 10
        .byte "NO A12 PULSES, RENDER OFF", 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i13:    .byte "PHASE 13: RENDER ON, NO A12", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i14:    .byte "PHASE 14: RENDER OFF LOOP", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i15:    .byte "PHASE 15: 231-CYCLE LOOP", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i16:    .byte "PHASE 16: PERIOD SCAN", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 0
i17:    .byte "PHASE 17: OLD-STYLE LOOP", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 10
        .byte "CH7 D0 3", 0
i18:    .byte "PHASE 18: FREE RUN L=0", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 10
        .byte "CH7 PPU12 21", 0
i19:    .byte "PHASE 19: FREE RUN L=1", 10, 10
        .byte "CH1 M2 12     CH2 R/W 13", 10
        .byte "CH3 ROMSEL 14 CH4 A0 15", 10
        .byte "CH5 A13 16    CH6 IRQ 40", 10
        .byte "CH7 PPU12 21", 0
s_foot: .byte 10, "GND ON J2 PIN 11.", 10
        .byte "SCREEN GOES BLANK IN 3 S,", 10
        .byte "THEN THE LOOP RUNS.", 10, 10
        .byte "RESET WITH A BUTTON HELD:", 10
        .byte "NONE/A 1  B 2  SELECT 3", 10
        .byte "START 4 UP 5 DOWN 6", 10
        .byte "LEFT 7  RIGHT 8", 10
        .byte "A+UP 9  A+DOWN 10", 10
        .byte "B+UP 11  B+DOWN 12", 10
        .byte "ST+UP 13  ST+DOWN 14", 10
        .byte "SEL+UP 15  SEL+DOWN 16", 10
        .byte "SEL+START 17", 10
        .byte "ST+LEFT 18  ST+RIGHT 19", 0

.include "common/lib.s"
