#!/usr/bin/env sh
set -e

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python"
fi

$PYTHON manage.py loaddata fixtures/demo.json
echo "Import termine: fixtures/demo.json"
