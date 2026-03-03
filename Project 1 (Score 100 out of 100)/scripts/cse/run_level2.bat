@echo off
title NSU Degree Audit - Level 2 - CSE CGPA ^& Waiver
cd /d "%~dp0..\.."
python src\cgpa_analyzer.py data\cse\transcript.csv
echo.
pause
