# claude-accounts

Keeps several Claude subscription logins and swaps between them automatically (see the docstring in `bin/claude-accounts`).
Works on **macOS and Linux** (not Windows). Needs Python 3.8+ as `python3` and Claude Code installed.

Install: `git clone https://github.com/Sipher/claude-accounts.git ~/claude-accounts && ~/claude-accounts/install.sh`
Then run `claude-accounts add` once per account and `claude-accounts watcher on`. Check with `claude-usage`.
Update: `git -C ~/claude-accounts pull && ~/claude-accounts/install.sh && claude-accounts watcher on` (rerun the installer to update hooks and reload the watcher).

To avoid anti-abuse bursts, the watcher checks every 15 minutes and usage reads are cached for 15 minutes. Heartbeats (starting idle accounts' 5-hour windows) never run in parallel: `claude-accounts prime` sends them one at a time, 90 seconds apart (`CLAUDE_ACCOUNTS_PRIME_GAP` to change), and stops at the first upstream error. The watcher does this automatically, but only while you're working (the live account's window is open); `claude-accounts heartbeat off` turns that off. Upstream 403/429/5xx responses pause usage polling for at least 15 minutes; a Cloudflare 403 on a model request does not invalidate a saved login. These safeguards reduce traffic but cannot guarantee that an upstream Cloudflare block will clear.

Where logins live (never copied off the machine):
- macOS: the login keychain (Claude Code's own item, plus one `claude-accounts` item per account).
- Linux: `~/.claude/.credentials.json` (Claude Code's own plaintext file) plus one 0600 file per account in `~/.claude/accounts/slots/`.

Watcher: launchd on macOS; on Linux a systemd user timer (runs while you're logged in; `loginctl enable-linger $USER` keeps it running after logout), or cron when there's no systemd user session. Desktop notifications use `notify-send` on Linux when available; everything is also logged to `~/.claude/accounts/log`.
