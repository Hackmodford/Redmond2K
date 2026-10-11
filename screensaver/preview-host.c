/* Redmond2K screen saver preview host (runs under Wine).
 *
 * Windows previews a screen saver by running "saver.scr /p <HWND>", which
 * makes the saver draw into a child of that window. A GTK window has no
 * HWND, so this program provides one: it opens a borderless WIDTHxHEIGHT
 * window at X,Y titled TITLE (redmond2k-screensaver.py finds it by that
 * title and reparents its X window into the monitor picture), then runs the
 * saver against it. It exits when the saver does, and takes the saver down
 * with it when it is closed or killed. Like saver-run.exe, it loads
 * saver-timer.dll into the saver (see start-saver.h).
 *
 * Usage: preview-host.exe TITLE X Y WIDTH HEIGHT C:\path\to\saver.scr
 * Built by install.sh:
 *   i686-w64-mingw32-gcc -municode -mwindows -Os -s \
 *       -o preview-host.exe preview-host.c
 */
#include "start-saver.h"
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>

static LRESULT CALLBACK wndproc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    if (msg == WM_DESTROY) {
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, LPWSTR cmdline, int show)
{
    int argc;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argc != 7)
        return 2;
    int x = _wtoi(argv[2]), y = _wtoi(argv[3]);
    int width = _wtoi(argv[4]), height = _wtoi(argv[5]);

    /* All sizes are device pixels. Without this, a Wine prefix set to a
     * high DPI scales our window up and it overflows the monitor picture. */
    SetProcessDPIAware();

    WNDCLASSW wc = {0};
    wc.lpfnWndProc = wndproc;
    wc.hInstance = inst;
    wc.hbrBackground = GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = L"Redmond2KPreviewHost";
    RegisterClassW(&wc);

    /* A captionless popup becomes an unmanaged X window under Wine, so the
     * window manager never decorates it. X,Y is where the GTK app's preview
     * already is, so nothing flashes before it adopts the window. (Starting
     * off screen doesn't work: Wine never maps windows outside the screen.)
     */
    HWND hwnd = CreateWindowExW(WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                                wc.lpszClassName, argv[1],
                                WS_POPUP | WS_VISIBLE,
                                x, y, width, height,
                                NULL, NULL, inst, NULL);
    if (!hwnd)
        return 1;

    /* The saver gets its own Unix process group under Wine, so killing our
     * group would miss it. A kill-on-close job ties its life to ours. */
    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    limits.BasicLimitInformation.LimitFlags =
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                            &limits, sizeof limits);

    wchar_t command[4096];
    _snwprintf(command, 4096, L"\"%ls\" /p %lu", argv[6],
               (unsigned long)(ULONG_PTR)hwnd);
    command[4095] = 0;
    PROCESS_INFORMATION pi;
    if (!start_saver(command, &pi))
        return 1;
    AssignProcessToJobObject(job, pi.hProcess);
    ResumeThread(pi.hThread);

    for (;;) {
        DWORD woke = MsgWaitForMultipleObjects(1, &pi.hProcess, FALSE,
                                               INFINITE, QS_ALLINPUT);
        if (woke == WAIT_OBJECT_0)
            return 0; /* saver exited */
        MSG msg;
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) {
                TerminateProcess(pi.hProcess, 0);
                return 0;
            }
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
}
