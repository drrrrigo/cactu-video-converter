/* Cactu GPL-3.0-or-later. Uses Windows APIs only, no C or C++ runtime.
 * The prerequisite check must run before Python/Qt can be loaded. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include "windows-runtime-config.h"

static SIZE_T length(const WCHAR *s) { SIZE_T n = 0; while (s[n]) ++n; return n; }
static void append(WCHAR *s, const WCHAR *t) {
    SIZE_T n = length(s), i = 0;
    while (t[i]) { s[n + i] = t[i]; ++i; }
    s[n + i] = 0;
}
static BOOL equal(const WCHAR *a, const WCHAR *b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
static WCHAR *arguments(void) {
    WCHAR *p = GetCommandLineW();
    if (*p == L'"') { ++p; while (*p && *p != L'"') ++p; if (*p) ++p; }
    else { while (*p && *p != L' ' && *p != L'\t') ++p; }
    while (*p == L' ' || *p == L'\t') ++p;
    return p;
}
static BOOL recent_enough(const VS_FIXEDFILEINFO *v) {
    DWORD a = v->dwFileVersionMS, b = v->dwFileVersionLS;
    return a > CACTU_VERSION_MS || (a == CACTU_VERSION_MS && b >= CACTU_VERSION_LS);
}
static BOOL prerequisite(const WCHAR *directory) {
    WCHAR *path = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 65536);
    BOOL ok = path != NULL;
    for (unsigned i = 0; ok && i < CACTU_DLL_COUNT; ++i) {
        path[0] = 0; append(path, directory); append(path, L"\\"); append(path, CACTU_DLLS[i]);
        DWORD ignored = 0, size = GetFileVersionInfoSizeW(path, &ignored);
        void *info = size ? HeapAlloc(GetProcessHeap(), 0, size) : NULL;
        VS_FIXEDFILEINFO *version = NULL; UINT version_size = 0;
        ok = info && GetFileVersionInfoW(path, 0, size, info)
            && VerQueryValueW(info, L"\\", (void **)&version, &version_size)
            && version_size >= sizeof(VS_FIXEDFILEINFO)
            && version->dwSignature == 0xfeef04bd && recent_enough(version);
        if (info) HeapFree(GetProcessHeap(), 0, info);
        if (ok) {
            HMODULE module = LoadLibraryExW(path, NULL, LOAD_LIBRARY_SEARCH_SYSTEM32);
            ok = module != NULL;
            if (module) FreeLibrary(module);
        }
    }
    if (path) HeapFree(GetProcessHeap(), 0, path);
    return ok;
}
void CactuMain(void) {
    WCHAR *args = arguments();
    BOOL check_only = equal(args, L"--check-prerequisites");
    WCHAR system[MAX_PATH];
    UINT size = GetSystemDirectoryW(system, MAX_PATH);
    const WCHAR *directory = system;
#ifdef CACTU_RUNTIME_TEST
    /* This opt-in test binary is never packaged. Production has no override. */
    if (!check_only) {
        int count = 0;
        WCHAR **values = CommandLineToArgvW(GetCommandLineW(), &count);
        if (!values || count != 2) ExitProcess(11);
        directory = values[1]; check_only = TRUE;
    }
#endif
    if (!size || size >= MAX_PATH || !prerequisite(directory)) {
        if (!check_only && MessageBoxW(NULL,
            L"Cactu requires the Microsoft Visual C++ v14 Redistributable (x64), "
            CACTU_MINIMUM_TEXT L" or newer.\n\nInstall or repair it using Microsoft's official download page, "
            L"then open Cactu again. No installer will be downloaded or run automatically.\n\n"
            CACTU_GUIDANCE L"\n\nOpen the official guidance page?",
            L"Cactu — Microsoft runtime required", MB_YESNO | MB_ICONINFORMATION) == IDYES)
            ShellExecuteW(NULL, L"open", CACTU_GUIDANCE, NULL, NULL, SW_SHOWNORMAL);
        ExitProcess(10);
    }
    if (check_only) ExitProcess(0);
    WCHAR *path = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 65536);
    WCHAR *command = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 131072);
    if (!path || !command) ExitProcess(11);
    DWORD n = GetModuleFileNameW(NULL, path, 32768);
    if (!n || n >= 32768) ExitProcess(11);
    while (n && path[n - 1] != L'\\') --n;
    path[n] = 0; append(path, L"CactuVideoConverter-core.exe");
    /* A Windows command line is limited to 32767 WCHAR including its terminator. */
    if (length(path) + length(args) + 5 >= 32767) ExitProcess(11);
    append(command, L"\""); append(command, path); append(command, L"\" "); append(command, args);
    STARTUPINFOW startup; PROCESS_INFORMATION process;
    /* Explicit initialization avoids compiler-generated CRT memset imports. */
    unsigned char *bytes = (unsigned char *)&startup;
    for (SIZE_T i = 0; i < sizeof(startup); ++i) bytes[i] = 0;
    startup.cb = sizeof(startup);
    if (!CreateProcessW(path, command, NULL, NULL, TRUE, 0, NULL, NULL, &startup, &process)) {
        MessageBoxW(NULL, L"Cactu could not start. Repair or extract the complete application folder.",
            L"Cactu startup error", MB_OK | MB_ICONERROR); ExitProcess(11);
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD result = 11; GetExitCodeProcess(process.hProcess, &result);
    CloseHandle(process.hThread); CloseHandle(process.hProcess);
    HeapFree(GetProcessHeap(), 0, command); HeapFree(GetProcessHeap(), 0, path);
    ExitProcess(result);
}
