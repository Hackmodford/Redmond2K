/* Shared by preview-host.c and saver-run.c: starts a saver, with
 * saver-timer.dll (next to the calling exe) loaded into it when
 * REDMOND2K_TIMER_TICK_US is set. See saver-timer.c for why.
 *
 * The saver is created suspended and the DLL loaded by a remote thread
 * calling LoadLibraryW, so it's in place before the saver's first SetTimer.
 * kernel32 sits at the same address in every 32-bit process, so our
 * LoadLibraryW address is valid in the saver too. The caller resumes the
 * saver's main thread.
 */
#include <windows.h>
#include <wchar.h>

static BOOL start_saver(wchar_t *command, PROCESS_INFORMATION *pi)
{
    STARTUPINFOW si = {sizeof si};
    if (!CreateProcessW(NULL, command, NULL, NULL, FALSE, CREATE_SUSPENDED,
                        NULL, NULL, &si, pi))
        return FALSE;

    wchar_t tick[16], dll[MAX_PATH];
    if (!GetEnvironmentVariableW(L"REDMOND2K_TIMER_TICK_US", tick, 16))
        return TRUE;
    DWORD len = GetModuleFileNameW(NULL, dll, MAX_PATH);
    wchar_t *slash = wcsrchr(dll, L'\\');
    if (!len || !slash || slash - dll + 17 > MAX_PATH)
        return TRUE;
    wcscpy(slash + 1, L"saver-timer.dll");

    SIZE_T size = (wcslen(dll) + 1) * sizeof(wchar_t);
    void *remote = VirtualAllocEx(pi->hProcess, NULL, size,
                                  MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote || !WriteProcessMemory(pi->hProcess, remote, dll, size, NULL))
        return TRUE;
    LPTHREAD_START_ROUTINE load = (LPTHREAD_START_ROUTINE)GetProcAddress(
        GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
    HANDLE thread = CreateRemoteThread(pi->hProcess, NULL, 0, load, remote,
                                       0, NULL);
    if (thread) {
        WaitForSingleObject(thread, 10000);
        CloseHandle(thread);
    }
    return TRUE;
}
