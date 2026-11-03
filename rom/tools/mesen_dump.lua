-- run N frames, then dump the RAMBO test-ROM result block ($0300 status, $0301-3 signature, $0304.. text) and stop
local frames = 0
function onFrame()
  frames = frames + 1
  if frames == 500 then
    local st = emu.read(0x300, emu.memType.nesMemory)
    local sig = string.format("%02X%02X%02X", emu.read(0x301, emu.memType.nesMemory), emu.read(0x302, emu.memType.nesMemory), emu.read(0x303, emu.memType.nesMemory))
    local t = {}
    for a = 0x304, 0x7FF do
      local c = emu.read(a, emu.memType.nesMemory)
      if c == 0 then break end
      t[#t+1] = string.char(c)
    end
    print(table.concat(t))
    print(string.format("status $%02X signature %s", st, sig))
    emu.stop(st)
  end
end
emu.addEventCallback(onFrame, emu.eventType.endFrame)
