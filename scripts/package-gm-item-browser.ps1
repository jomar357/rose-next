<#
Build a portable tester tool with only its loose item tables, translations,
item atlas, and the DDS sheets named by that atlas. No VFS or game install needed.
Run again after editing item data to refresh the tester package.
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
@'
ROSE GM Item Browser

Launch gm-item-browser.exe. Keep the data folder beside it; it loads automatically.
No game installation or VFS files are needed.

Search by name or ID, filter by item type and stats, and click Copy to copy the
/item command. Paste it into game chat. GM access is required in the game.
Select an item name for details and quantities on stackable items.

Open data folder selects another loose data set. Open VFS remains available for
loading a game's data.idx directly. Reload refreshes the selected source.

This catalog is a snapshot: update the package when the server's item data changes.
'@ | Set-Content -LiteralPath (Join-Path $packageRoot 'README.txt') -Encoding utf8

$size = (Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "Packaged $($assets.Count) loose data files ($sheetCount icon sheets)."
Write-Host ('Package: {0} ({1:N1} MB)' -f $packageRoot, ($size / 1MB))
