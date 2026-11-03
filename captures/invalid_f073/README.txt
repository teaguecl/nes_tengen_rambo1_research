These captures were taken with a timing probe image whose padding macros loaded a stray RAM byte into A, so the $C001 writes carried a
random mode bit (docs/findings.md, F-073, withdrawn). They are kept only as the record of how the bug was found, and as the data behind the
evidence that D0 was high at the end of the $C001 write (pwr/p17_cold_1.sr, tools/la_d0_analysis.py). Do not use them as chip behaviour.
Valid replacements: captures/p9c_*, p10c_*, p11_*, p18_*, p19_* and pwr/p17_fixed.sr.
