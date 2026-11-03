; Probe for the cycle-exact delay primitive: runs `ldx #q / jsr delay_q` for several q so that an emulator script (or a
; logic analyser) can measure the cycles between each JSR and the instruction after it. Expected: 32q + 11 cycles.
; Not a test ROM: tools/delay_check.sh drives it on MesenCE and compares the measured cycle counts.
.include "common/vars.inc"

rom_title: .asciiz "DELAY PROBE"
rom_note:  .asciiz "NOT A TEST. SEE TOOLS."

test_table:
        TEST t_probe, n_probe, $FF
        .word 0

n_probe: .asciiz "DELAY BLOCKS RUN"

.include "common/cycles.s"

.macro PROBE q, jlabel, nlabel
        ldx #q
jlabel: jsr delay_q
nlabel:
.endmacro

t_probe:
        PROBE 1, p1_j, p1_n
        PROBE 2, p2_j, p2_n
        PROBE 3, p3_j, p3_n
        PROBE 7, p7_j, p7_n
        PROBE 30, p30_j, p30_n
        PROBE 34, p34_j, p34_n
        lda #0
        rts

.include "common/lib.s"
