#!/usr/bin/env bash
# Run this script ON PythonAnywhere (Bash console), not on your PC.
# Use: bash pythonanywhere_setup.sh   (do not use `sh`; it is not bash.)
# Prerequisites (one-time): Databases tab → Initialize MySQL and set your MySQL password.
#
# Required environment variables for this session:
#   export MYSQL_PASSWORD='your-mysql-password'
#   export DEPLOY_USER_PASSWORD='password-for-admin-manager-employee'
#
# Optional:
#   export REPO_URL='https://github.com/YourOrg/Bakery.git'
#   export PA_USER='anirden2020'
#   export SECRET_KEY='...'   # generated if omitted
#
if [ -z "${BASH_VERSION:-}" ]; then
  echo "ERROR: Run with bash, not sh. Example: bash $0" >&2
  exit 1
fi
set -euo pipefail

PA_USER="${PA_USER:-anirden2020}"
REPO_URL="${REPO_URL:-https://github.com/Emiya145/Bakery.git}"
PROJECT_DIR="${HOME}/bakery"
DB_HOST="${DB_HOST:-${PA_USER}.mysql.pythonanywhere-services.com}"
# Database name must be literally username$bakery on PythonAnywhere
DB_NAME="${DB_NAME:-${PA_USER}\$bakery}"
SITE_HOST="${SITE_HOST:-${PA_USER}.pythonanywhere.com}"
SITE_ORIGIN="https://${SITE_HOST}"

if [[ -z "${MYSQL_PASSWORD:-}" ]]; then
  echo "ERROR: Set MYSQL_PASSWORD (from PythonAnywhere Databases tab)."
  exit 1
fi
if [[ -z "${DEPLOY_USER_PASSWORD:-}" ]]; then
  echo "ERROR: Set DEPLOY_USER_PASSWORD for admin, manager, and employee accounts."
  exit 1
fi

for cmd in git python3 mysql; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd"
    exit 1
  fi
done

if ! command -v npm >/dev/null 2>&1; then
  cat << 'NODEHELP'
ERROR: npm is not installed. On PythonAnywhere, install Node via nvm, for example:

  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  source ~/.nvm/nvm.sh
  nvm install 20
  nvm use 20

Then re-run this script.
NODEHELP
  exit 1
fi

if [[ ! -d "$PROJECT_DIR/.git" ]]; then
  git clone "$REPO_URL" "$PROJECT_DIR"
else
  git -C "$PROJECT_DIR" pull --rebase || true
fi

cd "$PROJECT_DIR"

VENV_DIR="${PROJECT_DIR}/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

cd "${PROJECT_DIR}/frontend"
npm ci
NODE_ENV=production npm run build
cd "$PROJECT_DIR"

MYSQL_CREATE="CREATE DATABASE IF NOT EXISTS \`${PA_USER}\$bakery\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u "$PA_USER" -h "$DB_HOST" -p"$MYSQL_PASSWORD" -e "$MYSQL_CREATE"

if [[ -z "${SECRET_KEY:-}" ]]; then
  SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
fi

ENV_FILE="${PROJECT_DIR}/.env"
{
  printf 'SECRET_KEY=%s\n' "$SECRET_KEY"
  printf '%s\n' 'DEBUG=False'
  printf '%s\n' 'DJANGO_SETTINGS_MODULE=bakery.settings.prod'
  printf 'ALLOWED_HOSTS=%s\n' "$SITE_HOST"
  printf 'DB_NAME=%s\n' "$DB_NAME"
  printf 'DB_USER=%s\n' "$PA_USER"
  printf 'DB_PASSWORD=%s\n' "$MYSQL_PASSWORD"
  printf 'DB_HOST=%s\n' "$DB_HOST"
  printf 'CORS_ALLOWED_ORIGINS=%s\n' "$SITE_ORIGIN"
  printf 'CSRF_TRUSTED_ORIGINS=%s\n' "$SITE_ORIGIN"
} > "$ENV_FILE"

export DJANGO_SETTINGS_MODULE=bakery.settings.prod
export SECRET_KEY
export DEBUG=False
export ALLOWED_HOSTS="${SITE_HOST}"
export DB_NAME
export DB_USER="${PA_USER}"
export DB_PASSWORD="${MYSQL_PASSWORD}"
export DB_HOST
export CORS_ALLOWED_ORIGINS="${SITE_ORIGIN}"
export CSRF_TRUSTED_ORIGINS="${SITE_ORIGIN}"

python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py seed_sample_data --skip-users
export DEPLOY_USER_PASSWORD
python manage.py create_default_users

python manage.py check --deploy

echo ""
echo "==================================================================="
echo "Setup finished. Complete these steps in the PythonAnywhere dashboard:"
echo "==================================================================="
echo ""
echo "1) Web tab → Virtualenv: ${VENV_DIR}"
echo "2) Web tab → Static files → URL /static/ → Directory: ${PROJECT_DIR}/staticfiles/"
echo "3) Web tab → WSGI configuration file — use something like:"
echo ""
cat << WSGIEOF
import os, sys
from pathlib import Path

path = '${PROJECT_DIR}'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bakery.settings.prod')

env_file = Path(path) / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
WSGIEOF
echo ""
echo "4) Click Reload on the Web tab."
echo "5) Open: ${SITE_ORIGIN}/"
echo "   Admin: ${SITE_ORIGIN}/admin/  (users: admin, manager, employee)"
echo "==================================================================="
