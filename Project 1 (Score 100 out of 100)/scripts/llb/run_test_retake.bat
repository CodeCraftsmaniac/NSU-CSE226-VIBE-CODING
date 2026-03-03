@echo off
title NSU Degree Audit - Level 3 TEST - LLB Retake Scenario
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 3 Retake Scenario
echo   File: data/llb/test_retake.csv
echo   Tests: Triple retake (F-D-B), W then I then pass, F retake
echo ============================================================
echo.
python src\degree_audit.py data\llb\test_retake.csv LLB knowledge_base.md
echo.
pause
