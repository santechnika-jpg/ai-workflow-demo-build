@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=python"
    ) else (
        echo Nerastas Python 3.
        exit /b 1
    )
)

%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 exit /b 1

%PY_CMD% -m pip install -r requirements_exe.txt
if errorlevel 1 exit /b 1

%PY_CMD% -m PyInstaller --noconfirm AI_Workflow_Demo.spec
if errorlevel 1 exit /b 1

echo Build baigtas. EXE ieskokite:
echo dist\AI_Workflow_Demo.exe
exit /b 0
