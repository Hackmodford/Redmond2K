/* Redmond2K screen saver timer shim (runs under Wine).
 *
 * Loaded into a saver by saver-run.exe or preview-host.exe (see
 * start-saver.h). Old savers animate one step per WM_TIMER, and old Windows
 * only fired timers on its clock tick: 15.625 ms on Windows 2000, ~55 ms on
 * Windows 98. 3D Maze, for one, asks for 16 ms, which Windows 2000 rounded
 * up to two ticks (32 steps a second) but Wine honours exactly (62),
 * running it twice as fast as it ran there.
 *
 * If REDMOND2K_TIMER_TICK_US is set (the tick in microseconds), every
 * SetTimer call the saver makes is rounded up to whole ticks, the way the
 * old timer behaved. It works by rewriting the saver's import table entry
 * for user32's SetTimer.
 *
 * Built by install.sh:
 *   i686-w64-mingw32-gcc -shared -Os -s -o saver-timer.dll saver-timer.c
 */
#include <windows.h>
#include <stdlib.h>

static UINT tick_us;
static UINT_PTR (WINAPI *real_SetTimer)(HWND, UINT_PTR, UINT, TIMERPROC);

static UINT_PTR WINAPI rounded_SetTimer(HWND hwnd, UINT_PTR id, UINT ms,
                                        TIMERPROC proc)
{
    /* A timer fired on the first tick at or after its interval. */
    ULONGLONG ticks = ((ULONGLONG)ms * 1000 + tick_us - 1) / tick_us;
    if (!ticks)
        ticks = 1;
    return real_SetTimer(hwnd, id, (UINT)((ticks * tick_us + 500) / 1000),
                         proc);
}

/* Points every import table entry of module that resolves to user32's
 * SetTimer at rounded_SetTimer. Comparing addresses rather than names also
 * works for import tables whose name list the linker left out. */
static void patch_imports(HMODULE module)
{
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt =
        (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir =
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress)
        return;
    IMAGE_IMPORT_DESCRIPTOR *imp =
        (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress);
    for (; imp->Name; imp++) {
        IMAGE_THUNK_DATA *iat = (IMAGE_THUNK_DATA *)(base + imp->FirstThunk);
        for (; iat->u1.Function; iat++) {
            if (iat->u1.Function != (ULONG_PTR)real_SetTimer)
                continue;
            DWORD old;
            VirtualProtect(&iat->u1.Function, sizeof(iat->u1.Function),
                           PAGE_READWRITE, &old);
            iat->u1.Function = (ULONG_PTR)rounded_SetTimer;
            VirtualProtect(&iat->u1.Function, sizeof(iat->u1.Function), old,
                           &old);
        }
    }
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    char tick[16];
    if (reason != DLL_PROCESS_ATTACH)
        return TRUE;
    if (!GetEnvironmentVariableA("REDMOND2K_TIMER_TICK_US", tick, sizeof tick))
        return TRUE;
    tick_us = strtoul(tick, NULL, 10);
    real_SetTimer = (void *)GetProcAddress(GetModuleHandleA("user32.dll"),
                                           "SetTimer");
    if (tick_us && real_SetTimer)
        patch_imports(GetModuleHandleA(NULL));
    return TRUE;
}
