$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Missing venv Python at $Python. Run: py -3.11 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Push-Location $Root
try {
    & $Python scripts\create_sample_data.py
    & $Python make_model.py `
        --area data\sample\area.geojson `
        --buildings data\sample\buildings.geojson `
        --dem data\sample\dem.tif `
        --out output\sample_model.stl `
        --terrain-resolution 10 `
        --building-base-mode representative `
        --height-field HEIGHT `
        --floor-field GRND_FLR `
        --separate `
        --preview
    & $Python scripts\inspect_data.py `
        --area data\sample\area.geojson `
        --buildings data\sample\buildings.geojson `
        --dem data\sample\dem.tif
}
finally {
    Pop-Location
}
