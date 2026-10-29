#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review PARTNER_API_KEY before sharing the server."
fi
# Generate a strong local key on first setup if the user left it blank.
if grep -q '^PARTNER_API_KEY=$' .env; then
  partner_key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  sed -i "s/^PARTNER_API_KEY=$/PARTNER_API_KEY=${partner_key}/" .env
  echo "Generated PARTNER_API_KEY in .env. Copy the same value to the partner project securely."
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
python -m learning_japanese.main
