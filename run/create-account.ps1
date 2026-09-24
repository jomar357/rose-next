# Interactive wrapper around scripts/create-account.ps1 for local testing.
# Asks for a login name, a password (hidden) and an access level, then creates
# the account in the database named in dev/server/server.toml.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$toml = Join-Path $root "dev/server/server.toml"
if (-not (Test-Path $toml)) {
    throw "Missing $toml. See doc/ai/topics/project/local-setup-runbook.md."
}

# psql location: keep a PGBIN the user already set, else try Laragon's bundled PostgreSQL.
if (-not $env:PGBIN) {
    $laragon = "C:\laragon\bin\postgresql\postgresql\bin"
    if (Test-Path (Join-Path $laragon "psql.exe")) { $env:PGBIN = $laragon }
}

$name = Read-Host "Login name (6-30 characters)"
$secure = Read-Host "Password (8-30 characters)" -AsSecureString
$plain = [System.Net.NetworkCredential]::new("", $secure).Password
$level = Read-Host "Access level (Enter = 0 normal player, 2048 = full GM)"
if ([string]::IsNullOrWhiteSpace($level)) { $level = "0" }

& (Join-Path $root "scripts/create-account.ps1") -Email $name -Password $plain -AccessLevel ([int]$level) -ServerToml $toml
