@echo off
title NSU Degree Audit - Level 2 - LLB CGPA ^& Waiver
cd /d "%~dp0..\.."
python src\cgpa_analyzer.py data\llb\transcript.csv
echo.
pause
