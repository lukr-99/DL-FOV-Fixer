@echo off
REM Build DL-FOV-Fixer.exe (single-file, no console) with PyInstaller.
setlocal

python -m pip install -r requirements.txt pyinstaller || goto :err
python make_icon.py || goto :err

python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name DL-FOV-Fixer ^
    --icon assets\icon.ico ^
    --add-data "assets\icon.ico;assets" ^
    run.pyw || goto :err

echo.
echo Done. Executable is in: dist\DL-FOV-Fixer.exe
goto :eof

:err
echo.
echo Build failed.
exit /b 1
