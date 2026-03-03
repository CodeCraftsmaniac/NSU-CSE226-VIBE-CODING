@echo off
title NSU Degree Audit - Level 3 - CSE Degree Audit
cd /d "%~dp0..\.."
python src\degree_audit.py data\cse\transcript.csv CSE knowledge_base.md
echo.
pause
