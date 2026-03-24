@echo off
title NSU Degree Audit - Level 1 TEST - LLB Credit Edge Cases
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 1 Credit Tally (Edge Cases)
echo   File: data/llb/test_L1.csv
echo   Tests: F, W, I, P, TR, 0-credit course, D grade
echo ============================================================
echo.
python src\credit_engine.py data\llb\test_L1.csv
echo.
pause
