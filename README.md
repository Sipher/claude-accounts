# claude-accounts

Keeps several Claude subscription logins and swaps between them automatically (see the docstring in `bin/claude-accounts`).

Install on a Mac: `git clone git@github.com:Sipher/claude-accounts.git ~/claude-accounts && ~/claude-accounts/install.sh`
Then run `claude-accounts add` once per account and `claude-accounts watcher on`. Logins live in each Mac's keychain and are never copied.
Update: `git -C ~/claude-accounts pull`.
