#!/usr/bin/env bash
# run_server.sh — Pull latest code, sync venv + dependencies, and (re)start
# Gunicorn under nohup. Intended for the IJFINK backend on an Ubuntu VPS.
#
# Usage:
#   ./run_server.sh               # pull, sync, restart Gunicorn
#   ./run_server.sh --no-pull     # skip git pull (use local code)
#   ./run_server.sh --stop        # stop the running Gunicorn instance
#   ./run_server.sh --status      # show whether Gunicorn is running
#
# See README_Server.md → "Auto Run" for full documentation.

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
REQS_FILE="$PROJECT_DIR/requirements.txt"
LOG_FILE="$PROJECT_DIR/gunicorn.log"
BIND_ADDR="127.0.0.1:5000"
WORKERS="4"
GUNICORN_PATTERN="gunicorn -w ${WORKERS} -b ${BIND_ADDR} wsgi:app"

c_green="\033[1;32m"; c_yellow="\033[1;33m"; c_red="\033[1;31m"; c_reset="\033[0m"
log()  { echo -e "${c_green}[run_server]${c_reset} $*"; }
warn() { echo -e "${c_yellow}[run_server]${c_reset} $*"; }
err()  { echo -e "${c_red}[run_server]${c_reset} $*" >&2; }

stop_gunicorn() {
    if pgrep -f "$GUNICORN_PATTERN" >/dev/null; then
        log "Stopping existing Gunicorn process..."
        pkill -f "$GUNICORN_PATTERN" || true
        sleep 2
        if pgrep -f "$GUNICORN_PATTERN" >/dev/null; then
            warn "Gunicorn still alive — sending SIGKILL"
            pkill -9 -f "$GUNICORN_PATTERN" || true
            sleep 1
        fi
    else
        log "No running Gunicorn process found."
    fi
}

show_status() {
    if pgrep -af "$GUNICORN_PATTERN" >/dev/null; then
        log "Gunicorn is running:"
        pgrep -af "$GUNICORN_PATTERN"
        if command -v ss >/dev/null; then
            ss -tuln | grep ":5000" || true
        fi
    else
        warn "Gunicorn is NOT running."
        exit 1
    fi
}

DO_PULL=1
case "${1:-}" in
    --no-pull) DO_PULL=0 ;;
    --stop)    stop_gunicorn; exit 0 ;;
    --status)  show_status; exit 0 ;;
    "")        ;;
    *) err "Unknown option: $1"; exit 1 ;;
esac

cd "$PROJECT_DIR"

if [[ $DO_PULL -eq 1 ]]; then
    if [[ -d .git ]]; then
        log "Pulling latest code (git pull --ff-only)..."
        git pull --ff-only
    else
        warn "Not a git repository — skipping pull."
    fi
else
    log "Skipping git pull (--no-pull)."
fi

if [[ ! -d "$VENV_DIR" ]]; then
    log "No venv found — creating $VENV_DIR"
    python3 -m venv "$VENV_DIR"
else
    log "Reusing existing venv: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Upgrading pip..."
pip install --upgrade pip >/dev/null

if [[ ! -f "$REQS_FILE" ]]; then
    err "requirements.txt not found at $REQS_FILE"
    exit 1
fi

# Sync installed packages with requirements.txt. Compares freeze output
# against the file; runs pip install only if something is missing or mismatched.
log "Checking installed packages against requirements.txt..."
MISSING=0
while IFS= read -r raw_line; do
    line="${raw_line%%#*}"
    line="$(echo "$line" | tr -d '[:space:]')"
    [[ -z "$line" ]] && continue
    pkg_name="$(echo "$line" | sed -E 's/[<>=!~].*//')"
    [[ -z "$pkg_name" ]] && continue
    if ! pip show "$pkg_name" >/dev/null 2>&1; then
        warn "Missing package: $pkg_name"
        MISSING=1
    fi
done < "$REQS_FILE"

if [[ $MISSING -eq 1 ]]; then
    log "Installing requirements..."
    pip install -r "$REQS_FILE"
else
    log "All requirements present — running pip install to verify versions..."
    pip install -r "$REQS_FILE" --quiet
fi

stop_gunicorn

log "Starting Gunicorn under nohup..."
nohup "$VENV_DIR/bin/gunicorn" -w "$WORKERS" -b "$BIND_ADDR" wsgi:app \
    > "$LOG_FILE" 2>&1 &
disown || true

sleep 2

if pgrep -f "$GUNICORN_PATTERN" >/dev/null; then
    log "Gunicorn started. Logs: $LOG_FILE"
    log "Health check: curl http://localhost:5000/health"
else
    err "Gunicorn failed to start. Last 20 log lines:"
    tail -n 20 "$LOG_FILE" >&2 || true
    exit 1
fi
