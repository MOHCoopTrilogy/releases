@echo off
REM Volumetric clouds V2 offline unit test (plan 2.8) - needs the MSVC toolchain (vcvars64) and Python with the P0 twin's
REM deps (numpy, numba, PIL). Compiles openmohaa-hzm-vcl/code/renderergl2/tr_hzm_clouds_pure.h UNCHANGED with
REM vcl_selftest.c, checks it against the twin's bytes (make_refs.py), then proves the test can FAIL on broken copies.
REM A console program - no window, no game. Outputs go to %TEMP%\vcl_selftest.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
set GL2=%~dp0..\..\..\openmohaa-hzm-vcl\code\renderergl2
set OUT=%TEMP%\vcl_selftest
if not exist "%OUT%" mkdir "%OUT%"
set FLAGS=/nologo /W3 /O2 /MD /TC /fp:precise /D_CRT_SECURE_NO_WARNINGS

echo [1/4] reference bytes from the P0 twin
python "%~dp0make_refs.py" "%OUT%\refs" || goto :err

echo [2/4] compile (the header unchanged)
cl %FLAGS% /I"%GL2%" "%~dp0vcl_selftest.c" /Fo"%OUT%\\" /Fe"%OUT%\vcl_selftest.exe" >"%OUT%\build.log" 2>&1 || (type "%OUT%\build.log" & goto :err)

echo [3/4] run
"%OUT%\vcl_selftest.exe" "%OUT%\refs"
if errorlevel 1 goto :err

echo [4/4] prove it can fail: every broken copy of tr_hzm_clouds_pure.h must FAIL
set MUTOK=1
if exist "%OUT%\mut" rmdir /s /q "%OUT%\mut"
for /f "usebackq delims=" %%M in (`python "%~dp0mutate.py" "%GL2%\tr_hzm_clouds_pure.h" "%OUT%\mut"`) do (
  cl %FLAGS% /I"%%M" /I"%GL2%" "%~dp0vcl_selftest.c" /Fo"%%M\\" /Fe"%%M\t.exe" >"%%M\build.log" 2>&1 || (echo   could not build %%~nxM & set MUTOK=0)
  "%%M\t.exe" "%OUT%\refs" >"%%M\run.log" 2>&1 && (echo   %%~nxM: NOT caught & set MUTOK=0) || (for /f "delims=" %%L in ('findstr /b /c:"PASS" /c:"FAIL:" "%%M\run.log"') do echo   %%~nxM: caught - %%L)
)
if "%MUTOK%"=="0" goto :err
echo VCL SELFTEST: PASS
exit /b 0

:err
echo VCL SELFTEST: FAIL
exit /b 1
