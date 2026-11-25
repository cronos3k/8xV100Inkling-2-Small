# ---------------- V100 Inkling ----------------
$f['V100 Inkling - 1 Status.cmd'] = @'
@echo off
title V100 Inkling - status
call "%~dp0_config.cmd"
ssh %SSHO% %V100% "%INK%/ink-status.sh"
echo.
pause
'@

$f['V100 Inkling - 2 OpenCode on this PC (model on V100).cmd'] = @'
@echo off
title OpenCode on this PC - Inkling-2-Small on V100
call "%~dp0_config.cmd"
call "%~dp0_askdir.cmd" %1
if errorlevel 1 goto fail
set "V100_HOST=%V100%"
call "%LOCAL%\inkcode.cmd" "%PROJ%"
if errorlevel 1 goto fail
exit /b 0
:fail
pause
'@

$f['V100 Inkling - 3 OpenCode on the box (SSH).cmd'] = @'
@echo off
title OpenCode on the V100 box (SSH) - Inkling-2-Small
call "%~dp0_config.cmd"
set "RDIR="
set /p "RDIR=Project directory on the V100 box (Enter = home directory): "
if not defined RDIR set "RDIR=~"
ssh -t %SSHO% %V100% "%INK%/ink-code.sh %RDIR%"
if errorlevel 1 pause
'@

$f['V100 Inkling - 4 Start web interface with voice.cmd'] = @'
@echo off
title V100 Inkling - web interface
call "%~dp0_config.cmd"
echo Starts the Inkling model server if it is down (4-6 minutes), then the web interface.
echo The addresses are printed below; open the https one for your network.
ssh %SSHO% %V100% "%INK%/ink-web.sh"
echo.
pause
'@

$f['V100 Inkling - 5 Start model server (1M context).cmd'] = @'
@echo off
title V100 Inkling - start model server
call "%~dp0_config.cmd"
echo Only one model fits on the cards. If DeepSeek-V4.1-Flash is running, stop it first (V100 - 8).
echo Loading takes 4-6 minutes.
ssh %SSHO% %V100% "%INK%/ink-start.sh"
echo.
pause
'@

$f['V100 Inkling - 5b Start model server (8K context, quick tests).cmd'] = @'
@echo off
title V100 Inkling - start model server (short context)
call "%~dp0_config.cmd"
echo Only one model fits on the cards. If DeepSeek-V4.1-Flash is running, stop it first (V100 - 8).
ssh %SSHO% %V100% "%INK%/ink-start.sh short"
echo.
pause
'@

$f['V100 Inkling - 6 Stop web + voice.cmd'] = @'
@echo off
title V100 Inkling - stop web interface and speech
call "%~dp0_config.cmd"
echo The model server keeps running.
ssh %SSHO% %V100% "%INK%/ink-web-stop.sh"
echo.
pause
'@

$f['V100 Inkling - 7 Stop model server.cmd'] = @'
@echo off
title V100 Inkling - stop model server
call "%~dp0_config.cmd"
set "OK="
set /p "OK=Stop Inkling-2-Small on the V100 box? Loading it again takes 4-6 minutes. Type YES: "
if /i not "%OK%"=="YES" goto no
ssh %SSHO% %V100% "%INK%/ink-stop.sh"
goto end
:no
echo Not stopped.
:end
echo.
pause
'@

$f['V100 Inkling - 8 Switch to Inkling (stops DeepSeek, starts Inkling).cmd'] = @'
@echo off
title V100 - switch to Inkling-2-Small
call "%~dp0_config.cmd"
set "OK="
set /p "OK=Stop DeepSeek-V4.1-Flash and start Inkling-2-Small? Type YES: "
if /i not "%OK%"=="YES" goto no
ssh %SSHO% %V100% "~/coder/stop.sh; %INK%/ink-start.sh"
goto end
:no
echo Nothing changed.
:end
echo.
pause
'@

$f['V100 Inkling - 8b Switch back to DeepSeek (stops Inkling, starts DeepSeek).cmd'] = @'
@echo off
title V100 - switch to DeepSeek-V4.1-Flash
call "%~dp0_config.cmd"
set "OK="
set /p "OK=Stop Inkling-2-Small and start DeepSeek-V4.1-Flash? Type YES: "
if /i not "%OK%"=="YES" goto no
ssh %SSHO% %V100% "%INK%/ink-stop.sh && ~/coder/start.sh"
goto end
:no
echo Nothing changed.
:end
echo.
pause
'@

$f['V100 Inkling - 9 Close tunnel from this PC.cmd'] = @'
@echo off
call "%~dp0_config.cmd"
call "%LOCAL%\inkcode.cmd" -stop
pause
'@

