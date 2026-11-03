// Board definition for the Olimex RP2350-PICO2-BB48 module on the RAMBO-1 adapter (docs/rp2350_adapter_plan.md).
// RP2350B: 48 GPIO. No default UART/I2C/SPI/LED: the adapter uses the module's GPIO as in pins.h.
#ifndef _BOARDS_RAMBO_BB48_H
#define _BOARDS_RAMBO_BB48_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)

#define RAMBO_BB48
#define PICO_RP2350A 0

// Flash: assumed 2 MB (the smallest the module could have); raise it when the part is confirmed. [verify]
#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
#ifndef PICO_FLASH_SPI_CLKDIV
#define PICO_FLASH_SPI_CLKDIV 2
#endif
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (2 * 1024 * 1024))
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#endif

// GPIO23 is CHR_A15 on this adapter. Pico-style boards use GPIO23 to 25 for the regulator mode, VBUS sense and the LED; whether the
// Olimex module does is to be checked on the board [verify].
#endif
