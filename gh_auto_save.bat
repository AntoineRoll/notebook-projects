@echo off
setlocal enabledelayedexpansion

REM Check if Git is installed
where git > nul 2>nul
if %errorlevel% neq 0 (
    echo Git is not installed. Please install Git and try again.
    exit /b 1
)

REM Check if a folder is provided as an argument
if "%1"=="" (
    echo Usage: %~nx0 folder_path
    exit /b 1
) else (
    set folder=%CD%\%1%
)


REM Check if the folder is a Git repository
git rev-parse --git-dir > nul 2>nul
if %errorlevel% neq 0 (
    echo This folder is not a Git repository. Initialize Git first.
    exit /b 1
)

REM Add all files to the staging area
echo Adding files from %folder%
git add %folder%

REM Commit changes
set "commitMessage=Auto commit for %1 - %date% %time%"
git commit %folder% Readme.md .gitignore gh_auto_save.bat -m "%commitMessage%"
git push

echo Files committed successfully.
exit /b 0
