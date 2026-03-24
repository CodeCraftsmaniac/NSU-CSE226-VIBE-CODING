@echo off
title NSU Degree Audit - Level 1 - LLB Credit Tally
cd /d "%~dp0..\.."
python src\credit_engine.py data\llb\transcript.csv
echo.
pause
