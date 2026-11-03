-- log every entry of the G4 plain handler: interrupted PC and CPU cycle count (addresses from the linker label file)
local n = 0
local function rd(a) return emu.read(a, emu.memType.nesMemory) end
local function onIrq()
  n = n + 1
  if n <= 60 then
    local s = emu.getState()
    local sp = s["cpu.sp"]
    local pc = rd(0x100 + ((sp + 2) & 0xFF)) + 256 * rd(0x100 + ((sp + 3) & 0xFF))
    print(string.format("irq %d  pc %04X  cycle %d", n, pc, s["cpu.cycleCount"]))
  end
end
emu.addMemoryCallback(onIrq, emu.callbackType.exec, 0xE17B)
local frames = 0
function onFrame()
  frames = frames + 1
  if frames == 100 then emu.stop(0) end
end
emu.addEventCallback(onFrame, emu.eventType.endFrame)
