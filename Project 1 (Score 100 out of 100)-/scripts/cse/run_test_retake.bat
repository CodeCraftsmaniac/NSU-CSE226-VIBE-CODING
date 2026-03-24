@echo off
title NSU Degree Audit - Level 3 TEST - CSE Retake Scenario
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 3 Retake Scenario
echo   File: data/cse/test_retake.csv
echo   Tests: Triple retake, W then retake, F then retake
echo ============================================================
echo.
python src\degree_audit.py data\cse\test_retake.csv CSE knowledge_base.md
echo.
pause
