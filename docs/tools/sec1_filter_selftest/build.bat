@echo off
REM SEC1 filter self-test - MANUAL / engine-build step (needs the MSVC toolchain: vcvars64).
REM This is deliberately NOT wired into build.ps1: a script-only coop build on a shell without MSVC
REM must never be blocked by a C harness. Run it whenever cg_servercmds_filter.cpp changes.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"

echo [1/4] regenerate .inc from live engine + mod source
python gen.py || goto :err
python gen_inv.py >nul || goto :err

REM prove inv.inc is reproducible (no stale hand-edit survives): regenerate a second time and diff.
copy /y inv.inc inv.gen1 >nul
python gen_inv.py >nul || goto :err
fc /b inv.inc inv.gen1 >nul || (echo inv.inc is NOT reproducible & goto :err)
del inv.gen1 >nul 2>&1

set FLAGS=/nologo /W3 /wd4996 /wd4013 /wd4700 /wd4267 /wd4244 /wd4100

echo [2/4] compile patched (working-tree) harness
cl %FLAGS% /DIS_PATCHED /DSEC1_SELFTEST harness.c /Fework.exe /Fowork.obj >work_build.log 2>&1 || (type work_build.log & goto :err)

echo [3/4] compile head (committed pre-SEC1) harness for the delta arm
cl %FLAGS% /DFILTER_HEAD harness.c /Fehead.exe /Fohead.obj >head_build.log 2>&1 || (type head_build.log & goto :err)

echo [4/4] run
echo ---- PATCHED (working tree): attacks must DROP, legit + replay must PASS ----
"%~dp0work.exe"
set WORKRC=%errorlevel%
echo ---- HEAD (committed): attacks must ADMIT (proves the fix is load-bearing) ----
"%~dp0head.exe"
set HEADRC=%errorlevel%

echo.
if %WORKRC%==0 if %HEADRC%==0 (echo SEC1 SELFTEST: PASS & exit /b 0)
echo SEC1 SELFTEST: FAIL  work=%WORKRC% head=%HEADRC%
exit /b 1

:err
echo SEC1 SELFTEST: BUILD ERROR
exit /b 1
