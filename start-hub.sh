#!/usr/bin/env bash
# Starts JupyterHub (behind the Caddy HTTPS proxy) detached so it survives logout.
cd "$(dirname "$0")"
export PATH="$HOME/.local/node/bin:$PATH"
# Load secrets (tokens) — not committed to git. See secrets.env.example.
[ -f secrets.env ] && source secrets.env
exec ./venv/bin/jupyterhub -f jupyterhub_config.py
