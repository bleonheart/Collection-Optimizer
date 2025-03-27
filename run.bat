@echo off
cd /d "%~dp0"
PowerShell -NoProfile -ExecutionPolicy Unrestricted -File "%~dp0collectionoptimizer.ps1"
pause