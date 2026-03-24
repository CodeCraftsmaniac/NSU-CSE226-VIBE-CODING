@echo off
title NSU Degree Audit - Level 2 TEST - LLB CGPA Math
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 2 CGPA ^& Waiver (Math Verification)
echo   File: data/llb/test_L2.csv
echo   Tests: W, I, P, TR excluded from GPA; retake; F in GPA
echo ============================================================
echo.
python src\cgpa_analyzer.py data\llb\test_L2.csv
echo.
pause
