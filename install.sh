#!/bin/bash
# Symlink the scripts into ~/.local/bin and merge the hooks into ~/.claude/settings.json. Safe to rerun.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
mkdir -p "$BIN" "$HOME/.claude"
ln -sf "$REPO/bin/claude-accounts" "$BIN/claude-accounts"
ln -sf claude-accounts "$BIN/claude-usage"
ln -sf "$REPO/bin/claude-net-rewake" "$BIN/claude-net-rewake"
chmod +x "$REPO"/bin/*
case "$(uname -s)" in Darwin|Linux) ;; *) echo "claude-accounts supports macOS and Linux only" >&2; exit 1;; esac
PY="$(command -v python3 || true)"
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
  echo "claude-accounts needs Python 3.8+ as python3 (e.g. apt install python3)" >&2; exit 1
fi
case "${SHELL:-}" in */zsh) RC="$HOME/.zshrc";; */bash) RC="$HOME/.bashrc";; *) RC="$HOME/.profile";; esac
case ":$PATH:" in *":$BIN:"*) ;; *)
  grep -qs '.local/bin' "$RC" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
  echo "added $BIN to PATH in $RC (open a new terminal)";; esac
command -v claude >/dev/null || [ -x "$BIN/claude" ] || echo "note: Claude Code (claude) is not on PATH yet; install it before claude-accounts add" >&2
"$PY" - "$HOME" <<'PY'
import json, os, sys
home = sys.argv[1]
path = os.path.join(home, ".claude", "settings.json")
s = json.load(open(path)) if os.path.exists(path) else {}
b = f"{home}/.local/bin"
want = {
  "SessionStart": [{"hooks": [{"type": "command", "command": f"{b}/claude-accounts sync --quiet", "timeout": 30, "async": True}]}],
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": f"{b}/claude-accounts prime --auto", "timeout": 180, "async": True}]}],
  "StopFailure": [
    {"matcher": "rate_limit|billing_error|authentication_failed", "hooks": [{"type": "command", "command": f"{b}/claude-accounts hook", "timeout": 180, "asyncRewake": True}]},
    {"matcher": "overloaded|server_error|unknown", "hooks": [{"type": "command", "command": f"{b}/claude-net-rewake", "timeout": 1900, "asyncRewake": True}]},
  ],
}
mine = lambda g: any(("claude-accounts" in h.get("command", "") or "claude-net-rewake" in h.get("command", "")) for h in g.get("hooks", []))
hooks = s.setdefault("hooks", {})
for ev, groups in want.items():
    hooks[ev] = [g for g in hooks.get(ev, []) if not mine(g)] + groups
json.dump(s, open(path, "w"), indent=2); open(path, "a").write("\n")
print("hooks merged into", path)
PY
echo "Next: claude-accounts add (once per account), then claude-accounts watcher on"
