@echo off
title NSU Degree Audit - Level 1 TEST - CSE Credit Edge Cases
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 1 Credit Tally (Edge Cases)
echo   File: data/cse/test_L1.csv
echo   Tests: F, W, I, P, TR, 0-credit lab, D grade
echo ============================================================
echo.
python src\credit_engine.py data\cse\test_L1.csv
echo.
pause
