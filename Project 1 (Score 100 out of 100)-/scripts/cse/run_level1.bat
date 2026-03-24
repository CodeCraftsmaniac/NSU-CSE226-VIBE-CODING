@echo off
title NSU Degree Audit - Level 1 - CSE Credit Tally
cd /d "%~dp0..\.."
python src\credit_engine.py data\cse\transcript.csv
echo.
pause

