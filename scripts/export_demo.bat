@echo off
setlocal

if not exist fixtures mkdir fixtures

if exist .venv\Scripts\python.exe (
  set PYTHON=.venv\Scripts\python.exe
) else (
  set PYTHON=python
)

%PYTHON% manage.py dumpdata gestion --exclude auth --exclude contenttypes --exclude admin --exclude sessions --indent 2 > fixtures\demo.json
echo Export termine: fixtures\demo.json
