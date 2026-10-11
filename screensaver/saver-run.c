/* Redmond2K screen saver launcher (runs under Wine).
 *
 * Runs a saver with saver-timer.dll loaded into it (see start-saver.h) and
 * exits when it does. A kill-on-close job takes the saver down with us.
 *
 * Usage: saver-run.exe C:\path\to\saver.scr /s
 * Built by install.sh:
 *   i686-w64-mingw32-gcc -municode -mwindows -Os -s \
 *       -o saver-run.exe saver-run.c
 */
#include "start-saver.h"
#include <shellapi.h>
#include <stdio.h>

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, LPWSTR cmdline, int show)
{
    int argc;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argc < 2)
        return 2;

    wchar_t command[4096];
    int len = _snwprintf(command, 4096, L"\"%ls\"", argv[1]);
    for (int i = 2; i < argc && len > 0 && len < 4000; i++)
        len += _snwprintf(command + len, 4096 - len, L" %ls", argv[i]);
    command[4095] = 0;

    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    limits.BasicLimitInformation.LimitFlags =
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                            &limits, sizeof limits);

    PROCESS_INFORMATION pi;
    if (!start_saver(command, &pi))
        return 1;
    AssignProcessToJobObject(job, pi.hProcess);
    ResumeThread(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    return code;
}
