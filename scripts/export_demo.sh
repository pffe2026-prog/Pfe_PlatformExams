#!/usr/bin/env sh
set -e

mkdir -p fixtures

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python"
fi

$PYTHON manage.py dumpdata gestion --exclude auth --exclude contenttypes --exclude admin --exclude sessions --indent 2 > fixtures/demo.json
echo "Export termine: fixtures/demo.json"
