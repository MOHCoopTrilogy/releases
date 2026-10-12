@echo off
REM vram_pick_selftest - MANUAL / engine-build step (needs the MSVC toolchain: vcvars64). Run it whenever
REM renderergl2/tr_hzm_vram_pick.h changes. HZM_MENU_ENG = the engine tree's code dir (default: openmohaa-hzm\code).
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
set ENG=%HZM_MENU_ENG%
if "%ENG%"=="" set ENG=%~dp0..\..\..\openmohaa-hzm\code
cl /nologo /W3 /wd4996 /I"%ENG%\renderergl2" test.c /Fetest.exe /Fotest.obj >build.log 2>&1 || (type build.log & exit /b 1)
"%~dp0test.exe"
exit /b %errorlevel%
