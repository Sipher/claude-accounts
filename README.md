# claude-accounts

Keeps several Claude subscription logins and swaps between them automatically (see the docstring in `bin/claude-accounts`).
Works on **macOS and Linux** (not Windows). Needs Python 3.8+ as `python3` and Claude Code installed.

Install: `git clone https://github.com/Sipher/claude-accounts.git ~/claude-accounts && ~/claude-accounts/install.sh`
Then run `claude-accounts add` once per account and `claude-accounts watcher on`. Check with `claude-usage`.
Update: `git -C ~/claude-accounts pull`.

Where logins live (never copied off the machine):
- macOS: the login keychain (Claude Code's own item, plus one `claude-accounts` item per account).
- Linux: `~/.claude/.credentials.json` (Claude Code's own plaintext file) plus one 0600 file per account in `~/.claude/accounts/slots/`.

Watcher: launchd on macOS; on Linux a systemd user timer (runs while you're logged in; `loginctl enable-linger $USER` keeps it running after logout), or cron when there's no systemd user session. Desktop notifications use `notify-send` on Linux when available; everything is also logged to `~/.claude/accounts/log`.
