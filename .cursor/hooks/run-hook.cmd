: << 'CMDBLOCK'
@echo off
REM Polyglot Cursor hook launcher (Windows cmd + Unix bash).
REM hooks.json must NOT contain ".sh" — Windows may ShellExecute path tokens with .sh.
REM Usage: run-hook.cmd <basename>   e.g. run-hook.cmd commit-verify

if "%~1"=="" (
  echo {}
  exit /b 0
)

set "HOOK_DIR=%~dp0"
set "NAME=%~1"
if /I "%NAME:~-3%"==".sh" (
  set "HOOK_SCRIPT=%HOOK_DIR%%NAME%"
) else (
  set "HOOK_SCRIPT=%HOOK_DIR%%NAME%.sh"
)

if exist "C:\Program Files\Git\bin\bash.exe" (
  "C:\Program Files\Git\bin\bash.exe" "%HOOK_SCRIPT%"
  exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
  "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_SCRIPT%"
  exit /b %ERRORLEVEL%
)
if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" (
  "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" "%HOOK_SCRIPT%"
  exit /b %ERRORLEVEL%
)

where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
  bash "%HOOK_SCRIPT%"
  exit /b %ERRORLEVEL%
)

echo {}
exit /b 0
CMDBLOCK

# Unix
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAME="${1:-}"
if [ -z "${NAME}" ]; then
  printf '{}\n'
  exit 0
fi
case "${NAME}" in
  *.sh) SCRIPT="${SCRIPT_DIR}/${NAME}" ;;
  *)    SCRIPT="${SCRIPT_DIR}/${NAME}.sh" ;;
esac
shift
exec bash "${SCRIPT}" "$@"
