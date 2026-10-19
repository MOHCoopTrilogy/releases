@echo off
REM r_hzmLodFog offline unit test (docs/proposals/fog_lod_pop_2026-09-27/plan.md section 5.1) - MANUAL / engine-build
REM step, needs the MSVC toolchain (vcvars64). Compiles openmohaa-hzm/code/renderergl2/tr_hzm_lodfog.c UNCHANGED against
REM the real tr_local.h with the renderer's own include paths and defines (same as hzm_spot_selftest), plus
REM hzm_lodfog_selftest.c; runs it. A console program - no window, no game. Outputs go to %TEMP%\hzm_lodfog_selftest.
REM Run it whenever tr_hzm_lodfog.c or the hzmLodBand_t block in tr_local.h changes.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
set CODE=%~dp0..\..\..\openmohaa-hzm\code
set OUT=%TEMP%\hzm_lodfog_selftest
if not exist "%OUT%" mkdir "%OUT%"
set INC=/I"%CODE%\renderergl2" /I"%CODE%\sdl" /I"%CODE%\renderercommon" /I"%CODE%\thirdparty\jpeg-9f" /I"%CODE%\qcommon" /I"%CODE%\..\.cmake\code\qcommon\generated" /I"%CODE%\thirdparty\SDL2-2.32.8\include"
set DEFS=/DWIN32 /D_WINDOWS /DNDEBUG /DUSE_RENDERER_DLOPEN=1 /DREF_DLL=1 /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE /DUSE_INTERNAL_JPEG
set FLAGS=/nologo /W3 /O2 /MD /TC /fp:precise
cl %FLAGS% %INC% %DEFS% "%CODE%\renderergl2\tr_hzm_lodfog.c" "%~dp0hzm_lodfog_selftest.c" /Fo"%OUT%\\" /Fe"%OUT%\hzm_lodfog_selftest.exe" >"%OUT%\build.log" 2>&1 || (type "%OUT%\build.log" & exit /b 1)
"%OUT%\hzm_lodfog_selftest.exe"
exit /b %errorlevel%
