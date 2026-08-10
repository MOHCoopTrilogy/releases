@echo off
REM Front end for the derived-documentation generator.
REM   docs build   regenerate docs\generated\  (no-op if inputs unchanged)
REM   docs check   exit 1 if docs\generated is stale
REM   docs status  print fingerprint + staleness, write nothing
setlocal
set "MODE=%~1"
if "%MODE%"=="" set "MODE=build"
py -3 "%~dp0docgen.py" %MODE% %2 %3 2>nul
if not errorlevel 9009 goto :done
python "%~dp0docgen.py" %MODE% %2 %3
:done
exit /b %ERRORLEVEL%
