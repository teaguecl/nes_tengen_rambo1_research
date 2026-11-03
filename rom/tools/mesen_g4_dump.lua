-- G4 debug dump: tau table and the captured interrupt PCs after the ROM has finished (300 frames)
local frames = 0
local function rd(a) return emu.read(a, emu.memType.nesMemory) end
function onFrame()
  frames = frames + 1
  if frames == 300 then
    local t = {}
    for i = 0, 8 do t[#t+1] = string.format("%d", rd(0x248 + i) + 256 * rd(0x251 + i)) end
    print("tau[L=0 1 2 3 4 8 16 40 255]: " .. table.concat(t, " "))
    print(string.format("irq_count %d  pc0 %02X%02X pc1 %02X%02X", rd(0x0F), rd(0x244), rd(0x240), rd(0x245), rd(0x241)))
    emu.stop(0)
  end
end
emu.addEventCallback(onFrame, emu.eventType.endFrame)
