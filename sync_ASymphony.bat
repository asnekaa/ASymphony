@echo off
chcp 65001 >nul

set "SRC=C:\Users\pc\AppData\Roaming\Turing Complete\schematics\architecture\ASymphony"
set "DST=D:\Dev\Repos\ASymphony"

echo 正在同步 ASymphony...
echo.
echo 来源:
echo %SRC%
echo.
echo 目标:
echo %DST%
echo.

robocopy "%SRC%" "%DST%" /E /IS /IT /R:2 /W:1

echo.
echo 同步完成。
pause