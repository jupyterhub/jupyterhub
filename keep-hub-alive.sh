#!/usr/bin/env bash
# Watchdog: ensures JupyterHub is always running. If it's down, (re)start it
# fully detached. Safe to run repeatedly (e.g. from cron every couple minutes).
cd "$(dirname "$0")"
export PATH="$HOME/.local/node/bin:$PATH"

# Already listening on the internal hub port? Then nothing to do.
if ss -tln 2>/dev/null | grep -q '172.17.0.1:8000'; then
    exit 0
fi

# Not running -> start it detached so it survives this shell.
setsid bash ./start-hub.sh </dev/null >> jupyterhub.log 2>&1 &
disown
