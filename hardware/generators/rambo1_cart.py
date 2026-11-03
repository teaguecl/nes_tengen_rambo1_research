"""RAMBO-1 flash cart + jig board -- SKiDL netlist description.

Generated from the verified continuity map of Tengen 800032 Rev A (Rolling Thunder).
Edge pins use NESdev numbering. Run with SKiDL 1.2+ :  python rambo1_cart.py
Produces rambo1_cart.net, which KiCad PCB Editor imports via File > Import > Netlist.
"""
from skidl import *

def mkpart(ref, value, footprint, pins, description):
    return Part(tool=SKIDL, name=ref + "_part", ref=ref, tag=ref, value=value, footprint=footprint,
                description=description, pins=[Pin(num=n, name=nm) for n, nm in pins.items()])

# ---------------------------------------------------------------- parts
J1 = mkpart('J1', 'NES 72-pin edge', 'nes_cart:NES_Edge_72_P2.50mm',
    {1: 'GND', 2: 'CPU_A11', 3: 'CPU_A10', 4: 'CPU_A9', 5: 'CPU_A8', 6: 'CPU_A7', 7: 'CPU_A6', 8: 'CPU_A5', 9: 'CPU_A4', 10: 'CPU_A3', 11: 'CPU_A2', 12: 'CPU_A1', 13: 'CPU_A0', 14: 'CPU_RW', 15: 'IRQ_N', 16: 'EXP0', 17: 'EXP1', 18: 'EXP2', 19: 'EXP3', 20: 'EXP4', 21: 'PPU_RD_N', 22: 'CIRAM_A10', 23: 'PPU_A6', 24: 'PPU_A5', 25: 'PPU_A4', 26: 'PPU_A3', 27: 'PPU_A2', 28: 'PPU_A1', 29: 'PPU_A0', 30: 'PPU_D0', 31: 'PPU_D1', 32: 'PPU_D2', 33: 'PPU_D3', 34: 'CIC_TOPAK', 35: 'CIC_TOMB', 36: '+5V', 37: 'SYS_CLK', 38: 'M2', 39: 'CPU_A12', 40: 'CPU_A13', 41: 'CPU_A14', 42: 'CPU_D7', 43: 'CPU_D6', 44: 'CPU_D5', 45: 'CPU_D4', 46: 'CPU_D3', 47: 'CPU_D2', 48: 'CPU_D1', 49: 'CPU_D0', 50: 'ROMSEL_N', 51: 'EXP9', 52: 'EXP8', 53: 'EXP7', 54: 'EXP6', 55: 'EXP5', 56: 'PPU_WR_N', 57: 'CIRAM_CE_N', 58: 'PPU_A13_N', 59: 'PPU_A7', 60: 'PPU_A8', 61: 'PPU_A9', 62: 'PPU_A11', 63: 'PPU_A10', 64: 'PPU_A12', 65: 'PPU_A13', 66: 'PPU_D7', 67: 'PPU_D6', 68: 'PPU_D5', 69: 'PPU_D4', 70: 'CIC_RST', 71: 'CIC_CLK', 72: 'GND'},
    'Cartridge edge fingers, NESdev numbering, 2.50 mm pitch')
U1 = mkpart('U1', 'RAMBO-1 (Tengen 337006)', 'Package_DIP:DIP-40_W15.24mm',
    {1: 'M2', 2: 'PRG_A16', 3: 'PRG_A15', 4: 'PRG_A13', 5: 'PRG_CE_N', 6: 'D6', 7: 'A0', 8: 'D4', 9: 'D2', 10: 'RW', 11: 'ROMSEL_N', 12: 'CHR_A10', 13: 'PPU_A10', 14: 'PPU_A12', 15: 'CIC_TOPAK', 16: 'CIC_TOMB', 17: 'CIC_RST', 18: 'CIC_CLK', 19: 'GND_Q', 20: 'GND', 21: 'CHR_A16', 22: 'CHR_A17', 23: 'CHR_A15', 24: 'CHR_A14', 25: 'CHR_A12', 26: 'CHR_A13', 27: 'PPU_A11', 28: 'CHR_A11', 29: 'CIRAM_A10', 30: 'IRQ_N', 31: 'D3', 32: 'D1', 33: 'D0', 34: 'D5', 35: 'D7', 36: 'A14', 37: 'PRG_A14', 38: 'A13', 39: 'PRG_A17', 40: 'VCC'},
    'Mapper in HWS7264 40-pin ZIF')
U2 = mkpart('U2', 'SST39SF040 (PRG)', 'Package_DIP:DIP-40_W15.24mm',
    {1: 'A18', 2: 'A16', 3: 'A15', 4: 'A12', 5: 'A7', 6: 'A6', 7: 'A5', 8: 'A4', 9: 'A3', 10: 'A2', 11: 'A1', 12: 'A0', 13: 'DQ0', 14: 'DQ1', 15: 'DQ2', 16: 'VSS', 25: 'DQ3', 26: 'DQ4', 27: 'DQ5', 28: 'DQ6', 29: 'DQ7', 30: 'CE_N', 31: 'A10', 32: 'OE_N', 33: 'A11', 34: 'A9', 35: 'A8', 36: 'A13', 37: 'A14', 38: 'A17', 39: 'WE_N', 40: 'VDD', 17: 'NC', 18: 'NC', 19: 'NC', 20: 'NC', 21: 'NC', 22: 'NC', 23: 'NC', 24: 'NC'},
    'PRG flash in HWS7264; chip pin 1 at socket pin 1, socket 17-24 empty')
U3 = mkpart('U3', 'SST39SF040 (CHR)', 'Package_DIP:DIP-40_W15.24mm',
    {1: 'A18', 2: 'A16', 3: 'A15', 4: 'A12', 5: 'A7', 6: 'A6', 7: 'A5', 8: 'A4', 9: 'A3', 10: 'A2', 11: 'A1', 12: 'A0', 13: 'DQ0', 14: 'DQ1', 15: 'DQ2', 16: 'VSS', 25: 'DQ3', 26: 'DQ4', 27: 'DQ5', 28: 'DQ6', 29: 'DQ7', 30: 'CE_N', 31: 'A10', 32: 'OE_N', 33: 'A11', 34: 'A9', 35: 'A8', 36: 'A13', 37: 'A14', 38: 'A17', 39: 'WE_N', 40: 'VDD', 17: 'NC', 18: 'NC', 19: 'NC', 20: 'NC', 21: 'NC', 22: 'NC', 23: 'NC', 24: 'NC'},
    'CHR flash in HWS7264; chip pin 1 at socket pin 1, socket 17-24 empty')
U4 = mkpart('U4', '74HC04 (optional, DNP)', 'Package_DIP:DIP-14_W7.62mm',
    {1: '1A', 2: '1Y', 3: '2A', 4: '2Y', 5: '3A', 6: '3Y', 7: 'GND', 8: '4Y', 9: '4A', 10: '5Y', 11: '5A', 12: '6Y', 13: '6A', 14: 'VCC'},
    'Alternate PRG /OE source; fit only if JP1 set to 2-3')
U5 = mkpart('U5', 'ATtiny13A (fallback CIC, DNP)', 'Package_DIP:DIP-8_W7.62mm',
    {1: 'NC', 2: 'CLK', 3: 'LED', 4: 'GND', 5: 'DOUT', 6: 'DIN', 7: 'RST', 8: 'VCC'},
    'krikzz avrciczz; socketed, normally empty')
RN1 = mkpart('RN1', '220R isolated x8', 'Package_DIP:DIP-16_W7.62mm',
    {1: 'R1a', 2: 'R2a', 3: 'R3a', 4: 'R4a', 5: 'R5a', 6: 'R6a', 7: 'R7a', 8: 'R8a', 9: 'R8b', 10: 'R7b', 11: 'R6b', 12: 'R5b', 13: 'R4b', 14: 'R3b', 15: 'R2b', 16: 'R1b'},
    'Series R, J2 -> CPU D0-D7')
RN2 = mkpart('RN2', '220R isolated x8', 'Package_DIP:DIP-16_W7.62mm',
    {1: 'R1a', 2: 'R2a', 3: 'R3a', 4: 'R4a', 5: 'R5a', 6: 'R6a', 7: 'R7a', 8: 'R8a', 9: 'R8b', 10: 'R7b', 11: 'R6b', 12: 'R5b', 13: 'R4b', 14: 'R3b', 15: 'R2b', 16: 'R1b'},
    'Series R, J2 -> control + PPU A10/A11')
RN3 = mkpart('RN3', '220R isolated x8', 'Package_DIP:DIP-16_W7.62mm',
    {1: 'R1a', 2: 'R2a', 3: 'R3a', 4: 'R4a', 5: 'R5a', 6: 'R6a', 7: 'R7a', 8: 'R8a', 9: 'R8b', 10: 'R7b', 11: 'R6b', 12: 'R5b', 13: 'R4b', 14: 'R3b', 15: 'R2b', 16: 'R1b'},
    'Series R, J2 -> PPU A12 (7 spare)')
RN4 = mkpart('RN4', '10k bussed x9', 'Resistor_THT:R_Array_SIP10',
    {1: 'COM', 2: 'R1', 3: 'R2', 4: 'R3', 5: 'R4', 6: 'R5', 7: 'R6', 8: 'R7', 9: 'R8', 10: 'R9'},
    'Pull-ups on RAMBO inputs')
R8 = mkpart('R8', '1k bussed x8 (4609X-101-102)', 'Resistor_THT:R_Array_SIP9',
    {1: 'COM', 2: 'R1', 3: 'R2', 4: 'R3', 5: 'R4', 6: 'R5', 7: 'R6', 8: 'R7', 9: 'R8'},
    'CPU D0-D7 pull-ups, copies original R8')
R1 = mkpart('R1', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'PRG /WE pull-up')
R2 = mkpart('R2', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'CHR /WE pull-up')
R3 = mkpart('R3', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    '/IRQ pull-up')
R4 = mkpart('R4', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'RAMBO CIC toPak pull-down')
R5 = mkpart('R5', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'RAMBO CIC +RST pull-down')
R6 = mkpart('R6', '10k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'CIC CLK pull-down')
R7 = mkpart('R7', '1k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    {1: '1', 2: '2'},
    'CIC status LED')
C1 = mkpart('C1', '100nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    {1: '1', 2: '2'},
    'U1 decoupling')
C2 = mkpart('C2', '100nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    {1: '1', 2: '2'},
    'U2 decoupling')
C3 = mkpart('C3', '100nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    {1: '1', 2: '2'},
    'U3 decoupling')
C4 = mkpart('C4', '100nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    {1: '1', 2: '2'},
    'U4 decoupling')
C5 = mkpart('C5', '100nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    {1: '1', 2: '2'},
    'U5 decoupling')
C6 = mkpart('C6', '10uF', 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm',
    {1: '+', 2: '-'},
    'Bulk, near J1 pin 36')
D1 = mkpart('D1', 'LED', 'LED_THT:LED_D3.0mm',
    {1: 'K', 2: 'A'},
    'CIC status')
SW1 = mkpart('SW1', 'CTS 206-2ST', 'Button_Switch_THT:SW_DIP_SPSTx02_Slide_9.78x7.26mm_W7.62mm_P2.54mm',
    {1: '1A', 2: '2A', 3: '2B', 4: '1B'},
    'SW1A PRG /WE, SW1B CHR /WE (ON = write enable)')
J2 = mkpart('J2', 'On Shore 302-S401', 'Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical',
    {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10', 11: '11', 12: '12', 13: '13', 14: '14', 15: '15', 16: '16', 17: '17', 18: '18', 19: '19', 20: '20', 21: '21', 22: '22', 23: '23', 24: '24', 25: '25', 26: '26', 27: '27', 28: '28', 29: '29', 30: '30', 31: '31', 32: '32', 33: '33', 34: '34', 35: '35', 36: '36', 37: '37', 38: '38', 39: '39', 40: '40'},
    'Jig / logic analyzer header')
J3 = mkpart('J3', '1x6 header', 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
    {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6'},
    'RAMBO CIC lines, for later study')
JP1 = mkpart('JP1', 'PRG /OE source', 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2', 3: '3'},
    '1-2 (default): RAMBO PRG /CE; 2-3: U4 inverted R/W')
JP2 = mkpart('JP2', 'RAMBO 19 to GND', 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Closed by default; cut to test pin 19')
JP3 = mkpart('JP3', 'Edge 34 to RAMBO 15', 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Closed by default; open for ATtiny CIC')
JP4 = mkpart('JP4', 'Edge 35 to RAMBO 16', 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Closed by default; open for ATtiny CIC')
JP5 = mkpart('JP5', 'Edge 70 to RAMBO 17', 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Closed by default; open for ATtiny CIC')
JP6 = mkpart('JP6', 'RAMBO 15 to GND (= Tengen R6)', 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Open by default; close for ATtiny CIC')
JP7 = mkpart('JP7', 'RAMBO 17 to GND (= Tengen R7)', 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm',
    {1: '1', 2: '2'},
    'Open by default; close for ATtiny CIC')

# ---------------------------------------------------------------- nets
n_GND = Net('GND')
n_GND += J1.p[1], J1.p[72], U1.p[20], U2.p[16], U2.p[1], U3.p[16], U3.p[1], U4.p[7], U4.p[3], U4.p[5], U4.p[9], U4.p[11], U4.p[13], U5.p[4], R4.p[2], R5.p[2], R6.p[2], D1.p[1], C1.p[2], C2.p[2], C3.p[2], C4.p[2], C5.p[2], C6.p[2], JP2.p[2], JP6.p[2], JP7.p[2], J3.p[1], J3.p[6], J2.p[2], J2.p[11], J2.p[18], J2.p[22], J2.p[29], J2.p[38]
n_P5V = Net('+5V')
n_P5V += J1.p[36], U1.p[40], U2.p[40], U3.p[40], U4.p[14], U5.p[8], RN4.p[1], R8.p[1], R1.p[1], R2.p[1], R3.p[1], C1.p[1], C2.p[1], C3.p[1], C4.p[1], C5.p[1], C6.p[1], J2.p[1]
n_CPU_A0 = Net('CPU_A0')
n_CPU_A0 += J1.p[13], U2.p[12], U1.p[7], RN2.p[4], RN4.p[5]
n_CPU_A1 = Net('CPU_A1')
n_CPU_A1 += J1.p[12], U2.p[11]
n_CPU_A2 = Net('CPU_A2')
n_CPU_A2 += J1.p[11], U2.p[10]
n_CPU_A3 = Net('CPU_A3')
n_CPU_A3 += J1.p[10], U2.p[9]
n_CPU_A4 = Net('CPU_A4')
n_CPU_A4 += J1.p[9], U2.p[8]
n_CPU_A5 = Net('CPU_A5')
n_CPU_A5 += J1.p[8], U2.p[7]
n_CPU_A6 = Net('CPU_A6')
n_CPU_A6 += J1.p[7], U2.p[6]
n_CPU_A7 = Net('CPU_A7')
n_CPU_A7 += J1.p[6], U2.p[5]
n_CPU_A8 = Net('CPU_A8')
n_CPU_A8 += J1.p[5], U2.p[35]
n_CPU_A9 = Net('CPU_A9')
n_CPU_A9 += J1.p[4], U2.p[34]
n_CPU_A10 = Net('CPU_A10')
n_CPU_A10 += J1.p[3], U2.p[31]
n_CPU_A11 = Net('CPU_A11')
n_CPU_A11 += J1.p[2], U2.p[33]
n_CPU_A12 = Net('CPU_A12')
n_CPU_A12 += J1.p[39], U2.p[4]
n_CPU_A13 = Net('CPU_A13')
n_CPU_A13 += J1.p[40], U1.p[38], RN2.p[5], RN4.p[6]
n_CPU_A14 = Net('CPU_A14')
n_CPU_A14 += J1.p[41], U1.p[36], RN2.p[6], RN4.p[7]
n_CPU_D0 = Net('CPU_D0')
n_CPU_D0 += J1.p[49], U1.p[33], U2.p[13], R8.p[2], RN1.p[1]
n_J2_D0 = Net('J2_D0')
n_J2_D0 += RN1.p[16], J2.p[3]
n_CPU_D1 = Net('CPU_D1')
n_CPU_D1 += J1.p[48], U1.p[32], U2.p[14], R8.p[3], RN1.p[2]
n_J2_D1 = Net('J2_D1')
n_J2_D1 += RN1.p[15], J2.p[4]
n_CPU_D2 = Net('CPU_D2')
n_CPU_D2 += J1.p[47], U1.p[9], U2.p[15], R8.p[4], RN1.p[3]
n_J2_D2 = Net('J2_D2')
n_J2_D2 += RN1.p[14], J2.p[5]
n_CPU_D3 = Net('CPU_D3')
n_CPU_D3 += J1.p[46], U1.p[31], U2.p[25], R8.p[5], RN1.p[4]
n_J2_D3 = Net('J2_D3')
n_J2_D3 += RN1.p[13], J2.p[6]
n_CPU_D4 = Net('CPU_D4')
n_CPU_D4 += J1.p[45], U1.p[8], U2.p[26], R8.p[6], RN1.p[5]
n_J2_D4 = Net('J2_D4')
n_J2_D4 += RN1.p[12], J2.p[7]
n_CPU_D5 = Net('CPU_D5')
n_CPU_D5 += J1.p[44], U1.p[34], U2.p[27], R8.p[7], RN1.p[6]
n_J2_D5 = Net('J2_D5')
n_J2_D5 += RN1.p[11], J2.p[8]
n_CPU_D6 = Net('CPU_D6')
n_CPU_D6 += J1.p[43], U1.p[6], U2.p[28], R8.p[8], RN1.p[7]
n_J2_D6 = Net('J2_D6')
n_J2_D6 += RN1.p[10], J2.p[9]
n_CPU_D7 = Net('CPU_D7')
n_CPU_D7 += J1.p[42], U1.p[35], U2.p[29], R8.p[9], RN1.p[8]
n_J2_D7 = Net('J2_D7')
n_J2_D7 += RN1.p[9], J2.p[10]
n_M2 = Net('M2')
n_M2 += J1.p[38], U1.p[1], RN2.p[1], RN4.p[2]
n_CPU_RW = Net('CPU_RW')
n_CPU_RW += J1.p[14], U1.p[10], U4.p[1], SW1.p[1], RN2.p[2], RN4.p[3]
n_ROMSEL_N = Net('ROMSEL_N')
n_ROMSEL_N += J1.p[50], U1.p[11], U2.p[30], RN2.p[3], RN4.p[4]
n_IRQ_N = Net('IRQ_N')
n_IRQ_N += J1.p[15], U1.p[30], R3.p[2], J2.p[40]
n_PRG_A13 = Net('PRG_A13')
n_PRG_A13 += U1.p[4], U2.p[36], J2.p[23]
n_PRG_A14 = Net('PRG_A14')
n_PRG_A14 += U1.p[37], U2.p[37], J2.p[24]
n_PRG_A15 = Net('PRG_A15')
n_PRG_A15 += U1.p[3], U2.p[3], J2.p[25]
n_PRG_A16 = Net('PRG_A16')
n_PRG_A16 += U1.p[2], U2.p[2], J2.p[26]
n_PRG_A17 = Net('PRG_A17')
n_PRG_A17 += U1.p[39], U2.p[38], J2.p[27]
n_RAMBO_PRG_CE_N = Net('RAMBO_PRG_CE_N')
n_RAMBO_PRG_CE_N += U1.p[5], JP1.p[1], J2.p[28]
n_PRG_OE_N = Net('PRG_OE_N')
n_PRG_OE_N += JP1.p[2], U2.p[32]
n_RW_INV = Net('RW_INV')
n_RW_INV += U4.p[2], JP1.p[3]
n_PRG_WE_N = Net('PRG_WE_N')
n_PRG_WE_N += U2.p[39], R1.p[2], SW1.p[4]
n_PPU_A0 = Net('PPU_A0')
n_PPU_A0 += J1.p[29], U3.p[12]
n_PPU_A1 = Net('PPU_A1')
n_PPU_A1 += J1.p[28], U3.p[11]
n_PPU_A2 = Net('PPU_A2')
n_PPU_A2 += J1.p[27], U3.p[10]
n_PPU_A3 = Net('PPU_A3')
n_PPU_A3 += J1.p[26], U3.p[9]
n_PPU_A4 = Net('PPU_A4')
n_PPU_A4 += J1.p[25], U3.p[8]
n_PPU_A5 = Net('PPU_A5')
n_PPU_A5 += J1.p[24], U3.p[7]
n_PPU_A6 = Net('PPU_A6')
n_PPU_A6 += J1.p[23], U3.p[6]
n_PPU_A7 = Net('PPU_A7')
n_PPU_A7 += J1.p[59], U3.p[5]
n_PPU_A8 = Net('PPU_A8')
n_PPU_A8 += J1.p[60], U3.p[35]
n_PPU_A9 = Net('PPU_A9')
n_PPU_A9 += J1.p[61], U3.p[34]
n_PPU_A10 = Net('PPU_A10')
n_PPU_A10 += J1.p[63], U1.p[13], RN2.p[7], RN4.p[8]
n_PPU_A11 = Net('PPU_A11')
n_PPU_A11 += J1.p[62], U1.p[27], RN2.p[8], RN4.p[9]
n_PPU_A12 = Net('PPU_A12')
n_PPU_A12 += J1.p[64], U1.p[14], RN3.p[1], RN4.p[10]
n_PPU_A13 = Net('PPU_A13')
n_PPU_A13 += J1.p[65], U3.p[30]
n_PPU_RD_N = Net('PPU_RD_N')
n_PPU_RD_N += J1.p[21], U3.p[32]
n_PPU_WR_N = Net('PPU_WR_N')
n_PPU_WR_N += J1.p[56], SW1.p[2]
n_CHR_WE_N = Net('CHR_WE_N')
n_CHR_WE_N += U3.p[39], R2.p[2], SW1.p[3]
n_PPU_D0 = Net('PPU_D0')
n_PPU_D0 += J1.p[30], U3.p[13]
n_PPU_D1 = Net('PPU_D1')
n_PPU_D1 += J1.p[31], U3.p[14]
n_PPU_D2 = Net('PPU_D2')
n_PPU_D2 += J1.p[32], U3.p[15]
n_PPU_D3 = Net('PPU_D3')
n_PPU_D3 += J1.p[33], U3.p[25]
n_PPU_D4 = Net('PPU_D4')
n_PPU_D4 += J1.p[69], U3.p[26]
n_PPU_D5 = Net('PPU_D5')
n_PPU_D5 += J1.p[68], U3.p[27]
n_PPU_D6 = Net('PPU_D6')
n_PPU_D6 += J1.p[67], U3.p[28]
n_PPU_D7 = Net('PPU_D7')
n_PPU_D7 += J1.p[66], U3.p[29]
n_CHR_A10 = Net('CHR_A10')
n_CHR_A10 += U1.p[12], U3.p[31], J2.p[30]
n_CHR_A11 = Net('CHR_A11')
n_CHR_A11 += U1.p[28], U3.p[33], J2.p[31]
n_CHR_A12 = Net('CHR_A12')
n_CHR_A12 += U1.p[25], U3.p[4], J2.p[32]
n_CHR_A13 = Net('CHR_A13')
n_CHR_A13 += U1.p[26], U3.p[36], J2.p[33]
n_CHR_A14 = Net('CHR_A14')
n_CHR_A14 += U1.p[24], U3.p[37], J2.p[34]
n_CHR_A15 = Net('CHR_A15')
n_CHR_A15 += U1.p[23], U3.p[3], J2.p[35]
n_CHR_A16 = Net('CHR_A16')
n_CHR_A16 += U1.p[21], U3.p[2], J2.p[36]
n_CHR_A17 = Net('CHR_A17')
n_CHR_A17 += U1.p[22], U3.p[38], J2.p[37]
n_CIRAM_A10 = Net('CIRAM_A10')
n_CIRAM_A10 += J1.p[22], U1.p[29], J2.p[39]
n_CIRAM_CE_N = Net('CIRAM_CE_N')
n_CIRAM_CE_N += J1.p[57], J1.p[58]
n_J2_M2 = Net('J2_M2')
n_J2_M2 += RN2.p[16], J2.p[12]
n_J2_CPU_RW = Net('J2_CPU_RW')
n_J2_CPU_RW += RN2.p[15], J2.p[13]
n_J2_ROMSEL_N = Net('J2_ROMSEL_N')
n_J2_ROMSEL_N += RN2.p[14], J2.p[14]
n_J2_CPU_A0 = Net('J2_CPU_A0')
n_J2_CPU_A0 += RN2.p[13], J2.p[15]
n_J2_CPU_A13 = Net('J2_CPU_A13')
n_J2_CPU_A13 += RN2.p[12], J2.p[16]
n_J2_CPU_A14 = Net('J2_CPU_A14')
n_J2_CPU_A14 += RN2.p[11], J2.p[17]
n_J2_PPU_A10 = Net('J2_PPU_A10')
n_J2_PPU_A10 += RN2.p[10], J2.p[19]
n_J2_PPU_A11 = Net('J2_PPU_A11')
n_J2_PPU_A11 += RN2.p[9], J2.p[20]
n_J2_PPU_A12 = Net('J2_PPU_A12')
n_J2_PPU_A12 += RN3.p[16], J2.p[21]
n_EDGE_CIC_TOPAK = Net('EDGE_CIC_TOPAK')
n_EDGE_CIC_TOPAK += J1.p[34], JP3.p[1], U5.p[6]
n_EDGE_CIC_TOMB = Net('EDGE_CIC_TOMB')
n_EDGE_CIC_TOMB += J1.p[35], JP4.p[1], U5.p[5]
n_EDGE_CIC_RST = Net('EDGE_CIC_RST')
n_EDGE_CIC_RST += J1.p[70], JP5.p[1], U5.p[7]
n_CIC_CLK = Net('CIC_CLK')
n_CIC_CLK += J1.p[71], U1.p[18], U5.p[2], R6.p[1], J3.p[5]
n_RAMBO_CIC_TOPAK = Net('RAMBO_CIC_TOPAK')
n_RAMBO_CIC_TOPAK += JP3.p[2], U1.p[15], R4.p[1], JP6.p[1], J3.p[2]
n_RAMBO_CIC_TOMB = Net('RAMBO_CIC_TOMB')
n_RAMBO_CIC_TOMB += JP4.p[2], U1.p[16], J3.p[3]
n_RAMBO_CIC_RST = Net('RAMBO_CIC_RST')
n_RAMBO_CIC_RST += JP5.p[2], U1.p[17], R5.p[1], JP7.p[1], J3.p[4]
n_RAMBO_P19 = Net('RAMBO_P19')
n_RAMBO_P19 += U1.p[19], JP2.p[1]
n_LED_A = Net('LED_A')
n_LED_A += U5.p[3], R7.p[1]
n_LED_R = Net('LED_R')
n_LED_R += R7.p[2], D1.p[2]

# ---------------------------------------------------------------- power nets
n_P5V.drive = POWER
n_GND.drive = POWER

if __name__ == "__main__":
    generate_netlist()
