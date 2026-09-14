@echo off
REM SEC2 filter self-test - security layer 2: openmohaa.exe filters every SERVER-origin command line at
REM execution (per-byte origin in the command buffer, shared statement rules in qcommon/cmd_filter.c).
REM MANUAL / engine-build step: needs the MSVC toolchain (vcvars64), so build.ps1 never runs it. Run it when
REM qcommon/cmd.c, qcommon/cmd_filter.c, cgame/cg_servercmds_filter.cpp or the stufftext plumbing in
REM client/cl_cgame.cpp changes, and after any change to what the mod vstr's or what the server writes.
REM
REM Arms (harness2.c): L1 = HEAD exe + HEAD cgame (attacks must RUN), L2 = layer 2 alone (attacks drop with
REM COVX), L12 = the new pair, OLDCG = the previous cgame.dll on the new exe, OLDCG153 = the v1.5.3 cgame.dll
REM players actually have today (engine commit 9045a836) on the new exe, NEWCG = the new cgame.dll on the
REM previous exe, L1_153 = the v1.5.3 cgame on the previous exe (the pair as it shipped). The L1 vs L12 /
REM OLDCG / NEWCG corpus traces must be identical, as must L1_153 vs OLDCG153 - each comparison isolates layer
REM 2 against ONE layer 1, because the v1.5.3 reception filter itself admits a different set than HEAD's
REM (it drops "disconnect;wait 30000", which bug-2580 fixed). Every planted mutant must FAIL.
setlocal EnableDelayedExpansion
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
set Q=..\..\..\openmohaa-hzm\code\qcommon

echo [1/5] guard list current, inputs regenerated from live source
python ..\sec2_guardlist.py --check || goto :err
python ..\sec1_filter_selftest\gen_inv.py >nul || goto :err
python gen_sec2.py || goto :err

set FLAGS=/nologo /W3 /wd4996 /wd4013 /wd4267 /wd4244 /wd4100 /wd4090 /DWIN32 /D_WINDOWS /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE /DAPP_MODULE
for %%d in (o_l1 o_l2 o_l12 o_oldcg o_oldcg153 o_l1_153 o_newcg o_m1 o_m2 o_m3 o_m4 o_abi) do if not exist %%d mkdir %%d

echo [2/5] compile arms and planted mutants
cl %FLAGS% /DARM_L1 /Ihead /I%Q% /Foo_l1\ harness2.c head\cmd.c %Q%\q_shared.c /Fel1.exe >l1_build.log 2>&1 || (type l1_build.log & goto :err)
cl %FLAGS% /DARM_L2 /I%Q% /Foo_l2\ harness2.c %Q%\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Fel2.exe >l2_build.log 2>&1 || (type l2_build.log & goto :err)
cl %FLAGS% /DARM_L12 /I%Q% /Foo_l12\ harness2.c %Q%\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Fel12.exe >l12_build.log 2>&1 || (type l12_build.log & goto :err)
cl %FLAGS% /DARM_OLDCG /I%Q% /Foo_oldcg\ harness2.c %Q%\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Feoldcg.exe >oldcg_build.log 2>&1 || (type oldcg_build.log & goto :err)
cl %FLAGS% /DARM_OLDCG153 /I%Q% /Foo_oldcg153\ harness2.c %Q%\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Feoldcg153.exe >oldcg153_build.log 2>&1 || (type oldcg153_build.log & goto :err)
cl %FLAGS% /DARM_L1_153 /Ihead /I%Q% /Foo_l1_153\ harness2.c head\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Fel1_153.exe >l1_153_build.log 2>&1 || (type l1_153_build.log & goto :err)
cl %FLAGS% /DARM_NEWCG /Ihead /I%Q% /Foo_newcg\ harness2.c head\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Fenewcg.exe >newcg_build.log 2>&1 || (type newcg_build.log & goto :err)
cl %FLAGS% /DARM_L2 /I%Q% /Foo_m1\ harness2.c mut_vstrlocal\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Femut_vstrlocal.exe >mut_build.log 2>&1 || (type mut_build.log & goto :err)
cl %FLAGS% /DARM_L2 /I%Q% /Foo_m2\ harness2.c mut_noshift\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Femut_noshift.exe >>mut_build.log 2>&1 || (type mut_build.log & goto :err)
cl %FLAGS% /DARM_L2 /I%Q% /Foo_m3\ harness2.c mut_nomemmove\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Femut_nomemmove.exe >>mut_build.log 2>&1 || (type mut_build.log & goto :err)
cl %FLAGS% /DARM_L12 /I%Q% /Foo_m4\ harness2.c mut_lsforced\cmd.c %Q%\cmd_filter.c %Q%\q_shared.c /Femut_lsforced.exe >>mut_build.log 2>&1 || (type mut_build.log & goto :err)

set E=..\..\..\openmohaa-hzm\code
cl %FLAGS% /DABI_HEAD /Ihead /I%E%\cgame /I%Q% /I%E%\renderercommon /Foo_abi\abi_head.obj abi.c /Feabi_head.exe >abi_build.log 2>&1 || (type abi_build.log & goto :err)
cl %FLAGS% /I%E%\cgame /I%Q% /I%E%\renderercommon /Foo_abi\abi_work.obj abi.c /Feabi_work.exe >>abi_build.log 2>&1 || (type abi_build.log & goto :err)
for %%e in (abi_head abi_work l1 l2 l12 oldcg oldcg153 l1_153 newcg mut_vstrlocal mut_noshift mut_nomemmove mut_lsforced) do if not exist %%e.exe (echo missing %%e.exe & goto :err)
echo [3/5] run arms
"%~dp0l1.exe" --trace trace_l1.txt >l1_run.log 2>&1
set RC_L1=!errorlevel!
"%~dp0l2.exe" --trace trace_l2.txt >l2_run.log 2>&1
set RC_L2=!errorlevel!
"%~dp0l12.exe" --trace trace_l12.txt >l12_run.log 2>&1
set RC_L12=!errorlevel!
"%~dp0oldcg.exe" --trace trace_oldcg.txt >oldcg_run.log 2>&1
set RC_OLD=!errorlevel!
"%~dp0oldcg153.exe" --trace trace_oldcg153.txt >oldcg153_run.log 2>&1
set RC_OLD153=!errorlevel!
"%~dp0l1_153.exe" --only corpus --trace trace_l1_153.txt >l1_153_run.log 2>&1
set RC_L1153=!errorlevel!
"%~dp0newcg.exe" --trace trace_newcg.txt >newcg_run.log 2>&1
set RC_NEW=!errorlevel!
for %%a in (l1 l2 l12 oldcg oldcg153 l1_153 newcg) do (
  echo ---- arm %%a ----
  findstr /c:"FAIL" /c:"group " /c:"RESULT" /c:"skip " /c:"runs=" /c:"checked=" %%a_run.log
)

echo [4/5] corpus traces: the new pairs must execute legitimate coop traffic exactly like the shipped pair
python gen_sec2.py --compare trace_l1.txt trace_l12.txt
set RC_C12=!errorlevel!
python gen_sec2.py --compare trace_l1.txt trace_oldcg.txt
set RC_COLD=!errorlevel!
python gen_sec2.py --compare trace_l1_153.txt trace_oldcg153.txt
set RC_C153=!errorlevel!
python gen_sec2.py --compare trace_l1.txt trace_newcg.txt
set RC_CNEW=!errorlevel!

echo [ABI] new cgame.dll vs previous exe: Cmd_StuffServer appended exactly past the previous clientGameImport_t
"%~dp0abi_head.exe" >abi_head.txt 2>&1
"%~dp0abi_work.exe" >abi_work.txt 2>&1
python gen_sec2.py --abi abi_head.txt abi_work.txt
set RC_ABI=!errorlevel!

echo [5/5] planted mutants must FAIL with the harness's own rc=1 (a guard that cannot fail proves nothing)
set MUT=
"%~dp0mut_vstrlocal.exe" --only origin >mut_vstrlocal_run.log 2>&1
if !errorlevel!==1 (echo   caught: vstr expansion inserted as LOCAL) else (echo   MUTANT SURVIVED: vstr expansion inserted as LOCAL rc=!errorlevel! & set MUT=1)
"%~dp0mut_noshift.exe" --only origin >mut_noshift_run.log 2>&1
if !errorlevel!==1 (echo   caught: tags not moved by the InsertText shift) else (echo   MUTANT SURVIVED: tags not moved by the InsertText shift rc=!errorlevel! & set MUT=1)
"%~dp0mut_nomemmove.exe" --only origin >mut_nomemmove_run.log 2>&1
if !errorlevel!==1 (echo   caught: tags not moved by the Execute memmove) else (echo   MUTANT SURVIVED: tags not moved by the Execute memmove rc=!errorlevel! & set MUT=1)
"%~dp0mut_lsforced.exe" --only diff >mut_lsforced_run.log 2>&1
if !errorlevel!==1 (echo   caught: exe treats every client as the listen host) else (echo   MUTANT SURVIVED: exe treats every client as the listen host rc=!errorlevel! & set MUT=1)

echo.
if !RC_L1!==0 if !RC_L2!==0 if !RC_L12!==0 if !RC_OLD!==0 if !RC_OLD153!==0 if !RC_L1153!==0 if !RC_NEW!==0 if !RC_C12!==0 if !RC_COLD!==0 if !RC_C153!==0 if !RC_CNEW!==0 if !RC_ABI!==0 if not defined MUT (echo SEC2 SELFTEST: PASS & exit /b 0)
echo SEC2 SELFTEST: FAIL  L1=!RC_L1! L2=!RC_L2! L12=!RC_L12! OLDCG=!RC_OLD! OLDCG153=!RC_OLD153! L1_153=!RC_L1153! NEWCG=!RC_NEW! trace12=!RC_C12! traceOld=!RC_COLD! trace153=!RC_C153! traceNew=!RC_CNEW! abi=!RC_ABI! mutant-survived=!MUT!
exit /b 1

:err
echo SEC2 SELFTEST: BUILD ERROR
exit /b 1
