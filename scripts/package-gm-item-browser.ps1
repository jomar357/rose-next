<#
Build a portable tester tool with only its loose item tables, translations,
item atlas, and the DDS sheets named by that atlas. No VFS or game install needed.
Run again after editing item or monster data to refresh the tester package.

The monster tab needs LIST_NPC and its model tables, but not the meshes,
textures and motions they name: the browser writes those tables plus
ASSET_MANIFEST.TXT (every referenced model file that exists in the source),
so its missing-file checks match the full data exactly.
#>
[CmdletBinding()]
param (
    [string]$DataRoot = (Join-Path $PSScriptRoot '../data'),
    [string]$OutputDir = (Join-Path $PSScriptRoot '../dist/gm-item-browser')
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$sourceRoot = (Resolve-Path -LiteralPath $DataRoot).Path
$packageRoot = [IO.Path]::GetFullPath($OutputDir)
$packageData = Join-Path $packageRoot 'data'

# Refuse output over the source data: a package is always a separate copy.
if ($packageRoot -eq $sourceRoot -or $packageData -eq $sourceRoot -or
    $packageRoot.StartsWith($sourceRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputDir must be separate from the source data folder.'
}

# Keep the item table inventory in sync automatically with ItemCategory::stb_name.
$categorySource = Get-Content -LiteralPath (Join-Path $repoRoot 'src/tools/npc-shop-editor/src/data.rs') -Raw
$tableNames = [regex]::Matches($categorySource, 'ItemCategory::\w+ => "(LIST_\w+\.STB)"') |
    ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
if ($tableNames.Count -ne 14) { throw 'Could not resolve all 14 item tables from ItemCategory.' }
$assets = [Collections.Generic.List[string]]::new()
foreach ($name in $tableNames) {
    $assets.Add("3DDATA/STB/$name")
    $assets.Add("3DDATA/STB/$($name.Replace('.STB', '_S.STL'))")
}
$assets.Add('3DDATA/CONTROL/RES/ITEM1.TSI')
$assets.Add('3DDATA/STB/STR_ITEMPREFIX.STL')

# Read the atlas header rather than copying every texture in CONTROL/RES.
$atlasPath = Join-Path $sourceRoot '3DDATA/CONTROL/RES/ITEM1.TSI'
$reader = [IO.BinaryReader]::new([IO.File]::OpenRead($atlasPath))
try {
    $sheetCount = $reader.ReadUInt16()
    for ($i = 0; $i -lt $sheetCount; $i++) {
        $length = $reader.ReadUInt16()
        $bytes = $reader.ReadBytes($length)
        if ($bytes.Length -ne $length) { throw 'Truncated ITEM1.TSI sheet name.' }
        $name = [Text.Encoding]::UTF8.GetString($bytes).TrimEnd([char]0)
        $basename = [IO.Path]::GetFileName($name.Replace('/', '\'))
        if ([string]::IsNullOrWhiteSpace($basename)) { throw 'Empty ITEM1.TSI sheet name.' }
        $assets.Add("3DDATA/CONTROL/RES/$basename")
        $null = $reader.ReadUInt32() # color key
    }
} finally {
    $reader.Dispose()
}

$assets = @($assets | Sort-Object -Unique)
foreach ($asset in $assets) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $asset) -PathType Leaf)) {
        throw "Required asset is missing: $asset"
    }
}

Push-Location (Join-Path $repoRoot 'src')
try {
    & cargo +stable-i686-pc-windows-msvc build --release -p npc-shop-editor --bin gm-item-browser
    if ($LASTEXITCODE -ne 0) { throw 'GM item browser build failed.' }
} finally {
    Pop-Location
}

$null = New-Item -ItemType Directory -Path $packageRoot -Force
Copy-Item -LiteralPath (Join-Path $repoRoot 'bin/release/gm-item-browser.exe') -Destination $packageRoot -Force
foreach ($asset in $assets) {
    $destination = Join-Path $packageData $asset
    $null = New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force
    Copy-Item -LiteralPath (Join-Path $sourceRoot $asset) -Destination $destination -Force
    if ((Get-FileHash -LiteralPath $destination).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sourceRoot $asset)).Hash) {
        throw "Copied asset did not verify: $asset"
    }
}

# Monster tables + asset manifest. The release exe has no console, so wait on
# it explicitly and read its error output from a file.
$monsterLog = Join-Path ([IO.Path]::GetTempPath()) 'gm-browser-package-monsters.txt'
$process = Start-Process -FilePath (Join-Path $packageRoot 'gm-item-browser.exe') `
    -ArgumentList @('--package-monsters', "`"$sourceRoot`"", "`"$packageData`"") `
    -Wait -PassThru -NoNewWindow -RedirectStandardError $monsterLog
if ($process.ExitCode -ne 0) {
    throw "Packaging monster data failed:`n$(Get-Content -LiteralPath $monsterLog -Raw)"
}
$manifestCount = (Get-Content -LiteralPath (Join-Path $packageData 'ASSET_MANIFEST.TXT')).Count - 1

@'
ROSE GM Browser

Launch gm-item-browser.exe. Keep the data folder beside it; it loads automatically.
No game installation or VFS files are needed.

Items tab: search by name or ID, filter by item type and stats, and click Copy
to copy the /item command. Select an item name for details and quantities on
stackable items.

Monsters tab: search by name or ID (#123 matches exactly ID 123), filter by
level and HP, set the spawn count, and click Copy for the /mon command.
Names in rose are broken rows: the server refuses them, or they would spawn
invisible, untextured or frozen. Select one to see exactly why. An amber
status marks minor problems such as a missing weapon prop or a blank name.

Paste commands into game chat. GM access is required in the game.
Ctrl+F jumps to the search box; double-click a name to copy its command.

Open data folder selects another loose data set. Open VFS remains available for
loading a game's data.idx directly. Reload refreshes the selected source.

This catalog is a snapshot: update the package when the server's data changes.
'@ | Set-Content -LiteralPath (Join-Path $packageRoot 'README.txt') -Encoding utf8

$size = (Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "Packaged $($assets.Count) loose data files ($sheetCount icon sheets)."
Write-Host "Packaged monster tables with $manifestCount referenced model files in the manifest."
Write-Host ('Package: {0} ({1:N1} MB)' -f $packageRoot, ($size / 1MB))
