@echo off
rem CheckList - GUNCELLEME GONDER. Surumu sorar, gerisini build\publish.py yapar.
cd /d "%~dp0"
set /p CUR=<src\version.txt
echo Simdiki surum: %CUR%
set /p VER="Yeni surum (or. 0.1.1): "
if "%VER%"=="" ( echo [IPTAL] & pause & exit /b 1 )
set /p NOTES="Ne degisti (bos birakilabilir): "
python build\publish.py %VER% "%NOTES%"
if errorlevel 1 ( echo [HATA] Yukaridaki mesaja bak. )
pause
