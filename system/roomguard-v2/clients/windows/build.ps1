# Requires Zig 0.13 on PATH. Run in this directory.
zig cc -target x86_64-windows-gnu -O2 -municode -Wl,--subsystem,windows main.c -o RoomGuard.exe -luser32 -lshell32 -lgdi32
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
