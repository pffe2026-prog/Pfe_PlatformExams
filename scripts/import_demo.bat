@echo off
setlocal

if exist .venv\Scripts\python.exe (
  set PYTHON=.venv\Scripts\python.exe
) else (
  set PYTHON=python
)

%PYTHON% manage.py loaddata fixtures\demo.json
echo Import termine: fixtures\demo.json
