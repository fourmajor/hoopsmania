#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="${STATE_DIR:-$REPO_ROOT/.openclaw/state}"
mkdir -p "$STATE_DIR"

LABEL="${DISPATCHER_LAUNCHD_LABEL:-com.hoopsmania.issue-dispatcher}"
PLIST_PATH="${DISPATCHER_PLIST_PATH:-$HOME/Library/LaunchAgents/$LABEL.plist}"
PID_FILE="$STATE_DIR/issue-dispatcher.pid"
STDOUT_LOG="$STATE_DIR/issue-dispatcher.stdout.log"
STDERR_LOG="$STATE_DIR/issue-dispatcher.stderr.log"

usage() {
  echo "usage: $0 {install|uninstall|start|stop|restart|status|logs}" >&2
}

install_launchd() {
  mkdir -p "$(dirname "$PLIST_PATH")"
  cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>$SCRIPT_DIR/run_dispatcher.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$SCRIPT_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$STDOUT_LOG</string>
  <key>StandardErrorPath</key><string>$STDERR_LOG</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl load "$PLIST_PATH"
  echo "installed + loaded launchd service: $LABEL"
}

uninstall_launchd() {
  launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
  echo "uninstalled launchd service: $LABEL"
}

start_fallback() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "already running (pid $(cat "$PID_FILE"))"
    return
  fi
  nohup "$SCRIPT_DIR/run_dispatcher.sh" >>"$STDOUT_LOG" 2>>"$STDERR_LOG" &
  echo $! > "$PID_FILE"
  echo "started fallback dispatcher pid $(cat "$PID_FILE")"
}

stop_fallback() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    echo "stopped fallback dispatcher"
  else
    echo "fallback dispatcher not running"
  fi
}

status_fallback() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "fallback running pid $(cat "$PID_FILE")"
  else
    echo "fallback not running"
  fi
}

cmd="${1:-}"
case "$cmd" in
  install)
    if [[ "$(uname -s)" == "Darwin" ]]; then
      install_launchd
    else
      echo "launchd unsupported on this OS; using fallback start"
      start_fallback
    fi
    ;;
  uninstall)
    if [[ "$(uname -s)" == "Darwin" ]]; then
      uninstall_launchd
    else
      stop_fallback
    fi
    ;;
  start)
    if [[ "$(uname -s)" == "Darwin" ]] && [[ -f "$PLIST_PATH" ]]; then
      launchctl kickstart -k "gui/$(id -u)/$LABEL"
      echo "started launchd service: $LABEL"
    else
      start_fallback
    fi
    ;;
  stop)
    if [[ "$(uname -s)" == "Darwin" ]] && [[ -f "$PLIST_PATH" ]]; then
      launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
      launchctl load "$PLIST_PATH" >/dev/null 2>&1 || true
      launchctl stop "$LABEL" >/dev/null 2>&1 || true
      echo "stopped launchd service: $LABEL"
    else
      stop_fallback
    fi
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if [[ "$(uname -s)" == "Darwin" ]] && [[ -f "$PLIST_PATH" ]]; then
      launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | head -n 25 || echo "service not loaded"
    else
      status_fallback
    fi
    ;;
  logs)
    tail -n 100 "$STDOUT_LOG" "$STDERR_LOG" 2>/dev/null || true
    ;;
  *)
    usage
    exit 2
    ;;
esac
