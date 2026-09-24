# Local test launchers

Double-click these to test the game on this machine without typing commands.

| File | What it does |
|---|---|
| `start-all.bat` | Starts the three servers, waits 30 s for the game server to load, then starts the client |
| `start-servers.bat` | Starts login, world and game servers, each in its own window |
| `start-client.bat` | Copies a newer build from `bin\release` into `Exes\` (exe and `znzin.dll` together), then starts the client against `127.0.0.1` |
| `stop-client.bat` | Closes the client |
| `stop-servers.bat` | Stops the three servers immediately |
| `stop-all.bat` | Closes the client, then stops the servers |
| `create-account.bat` | Asks for a login name, password (hidden) and access level, and creates the account |

Before stopping the servers, log your character out in the client: the stop scripts end the server
processes at once, so anything not yet saved is lost.

They expect the layout set up in
[doc/ai/topics/project/local-setup-runbook.md](../doc/ai/topics/project/local-setup-runbook.md):
the release build in `bin\release`, the game data in `Exes\` (client) and `data\` (servers), and
the local server config `dev\server\server.toml`. None of those folders is in git; a fresh
checkout needs the runbook first. Server logs go to `dev\server\log\`.
