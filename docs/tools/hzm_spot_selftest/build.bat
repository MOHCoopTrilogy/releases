@echo off
REM Phase S offline unit test (vet_phaseS.md G4) - MANUAL / engine-build step, needs the MSVC toolchain (vcvars64).
REM Compiles openmohaa-hzm/code/renderergl2/tr_hzm_spot.c UNCHANGED, against the real tr_local.h with the renderer's
REM own include paths and defines (from the omohrenderergl2 vcxproj), plus hzm_spot_selftest.c; runs it.
REM A console program - no window, no game. Outputs go to %TEMP%\hzm_spot_selftest (nothing is written here).
REM Run it whenever tr_hzm_spot.c or renderercommon/hzm_light_restore.h changes.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
set CODE=%~dp0..\..\..\openmohaa-hzm\code
set OUT=%TEMP%\hzm_spot_selftest
if not exist "%OUT%" mkdir "%OUT%"

set INC=/I"%CODE%\renderergl2" /I"%CODE%\sdl" /I"%CODE%\renderercommon" /I"%CODE%\thirdparty\jpeg-9f" /I"%CODE%\qcommon" /I"%CODE%\..\.cmake\code\qcommon\generated" /I"%CODE%\thirdparty\SDL2-2.32.8\include"
set DEFS=/DWIN32 /D_WINDOWS /DNDEBUG /DUSE_RENDERER_DLOPEN=1 /DREF_DLL=1 /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE /DUSE_INTERNAL_JPEG
set FLAGS=/nologo /W3 /O2 /MD /TC /fp:precise

echo [1/3] compile tr_hzm_spot.c (unchanged) + hzm_spot_selftest.c
cl %FLAGS% %INC% %DEFS% "%CODE%\renderergl2\tr_hzm_spot.c" "%~dp0hzm_spot_selftest.c" /Fo"%OUT%\\" /Fe"%OUT%\hzm_spot_selftest.exe" >"%OUT%\build.log" 2>&1 || (type "%OUT%\build.log" & goto :err)
findstr /i /c:" warning " "%OUT%\build.log"

echo [2/3] run
"%OUT%\hzm_spot_selftest.exe"
if errorlevel 1 goto :err

echo [3/3] prove it can fail: every deliberately broken copy of tr_hzm_spot.c must FAIL the test
set MUTOK=1
for /f "usebackq delims=" %%M in (`python "%~dp0mutate.py" "%CODE%\renderergl2\tr_hzm_spot.c" "%OUT%\mut"`) do (
  cl %FLAGS% %INC% %DEFS% "%%M" "%~dp0hzm_spot_selftest.c" /Fo"%OUT%\mut\\" /Fe"%OUT%\mut\mut.exe" >"%OUT%\mut\build.log" 2>&1 || (echo   could not build %%~nM & type "%OUT%\mut\build.log" & set MUTOK=0)
  "%OUT%\mut\mut.exe" >"%OUT%\mut\run.log" 2>&1 && (echo   %%~nM: NOT caught & set MUTOK=0) || (for /f "delims=" %%L in ('findstr /b /c:"PASS" /c:"FAIL:" "%OUT%\mut\run.log"') do echo   %%~nM: caught - %%L)
)
if "%MUTOK%"=="0" goto :err
echo HZM SPOT SELFTEST: PASS
exit /b 0

:err
echo HZM SPOT SELFTEST: FAIL
exit /b 1
