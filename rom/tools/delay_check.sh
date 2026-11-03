#!/bin/sh
# Measure the cycle-exact delay primitive (common/cycles.s) in an emulator: cycles between each `jsr delay_q` and the next
# instruction must be 32q + 11. Usage: tools/delay_check.sh [path-to-MesenCE-binary]
cd "$(dirname "$0")/.." || exit 1
MESEN=${1:-$HOME/Downloads/Mesen}
TMP=build/probe; mkdir -p "$TMP"
make -s build/delay_probe.nes || exit 1
ca65 -g -I . -o "$TMP/p.o" delay_probe.s && ld65 -C rambo.cfg -Ln "$TMP/p.lbl" -o "$TMP/p.prg" "$TMP/p.o" || exit 1
{
  echo 'local res = {}'
  for q in 1 2 3 7 30 34; do
    j=$(awk -v n=".p${q}_j" '$3==n {print $2}' "$TMP/p.lbl"); n=$(awk -v n=".p${q}_n" '$3==n {print $2}' "$TMP/p.lbl")
    echo "local s$q"
    echo "emu.addMemoryCallback(function() s$q = emu.getState()[\"cpu.cycleCount\"] end, emu.callbackType.exec, 0x$j)"
    echo "emu.addMemoryCallback(function() if s$q and not res[$q] then res[$q] = emu.getState()[\"cpu.cycleCount\"] - s$q end end, emu.callbackType.exec, 0x$n)"
  done
  cat <<'LUA'
local frames = 0
emu.addEventCallback(function()
  frames = frames + 1
  if frames == 60 then
    local bad = 0
    for _, q in ipairs({1, 2, 3, 7, 30, 34}) do
      local want = 32 * q + 11
      local got = res[q]
      print(string.format("q=%2d  measured %s  expected %d  %s", q, tostring(got), want, got == want and "OK" or "MISMATCH"))
      if got ~= want then bad = bad + 1 end
    end
    emu.stop(bad)
  end
end, emu.eventType.endFrame)
LUA
} > "$TMP/check.lua"
echo "== delay_q in MesenCE"
timeout 90 "$MESEN" --testRunner "$TMP/check.lua" build/delay_probe.nes 2>&1 | grep -E "^q="
rm -f "$TMP"/p.o "$TMP"/p.prg "$TMP"/p.lbl "$TMP"/check.lua; rmdir "$TMP"
