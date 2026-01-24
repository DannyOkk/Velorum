#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$APP_DIR/db.sqlite3"
TEMPLATE_DB="$APP_DIR/seed/db_admin_template.sqlite3"

echo "==> Starting with APP_DIR=$APP_DIR"

# Si no hay DATABASE_URL, asumimos sqlite (como en Render sin DBURL)
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "==> DATABASE_URL not set. Using SQLite."

  # Si no existe la DB o está vacía, la inicializamos desde la template
  if [[ ! -f "$DB_PATH" ]] || [[ ! -s "$DB_PATH" ]]; then
    if [[ -f "$TEMPLATE_DB" ]]; then
      echo "==> Initializing SQLite DB from template..."
      cp "$TEMPLATE_DB" "$DB_PATH"
      chmod 664 "$DB_PATH" || true
      echo "==> DB initialized at $DB_PATH"
    else
      echo "!! Template DB not found at $TEMPLATE_DB"
      echo "!! Django will create a fresh empty sqlite DB."
    fi
  else
    echo "==> SQLite DB already exists. Skipping template copy."
  fi
else
  echo "==> DATABASE_URL is set. Using external DB."
fi

# Tu comando de start (tal cual lo pediste)
bash -c "python manage.py makemigrations && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn -b 0.0.0.0:$PORT Velorum.wsgi:application"
