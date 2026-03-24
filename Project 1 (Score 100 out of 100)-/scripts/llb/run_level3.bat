@echo off
title NSU Degree Audit - Level 3 - LLB Degree Audit
cd /d "%~dp0..\.."
python src\degree_audit.py data\llb\transcript.csv LLB knowledge_base.md
echo.
pause
