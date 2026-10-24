<# Read-only launcher. Probe interpreters before auditing; never install dependencies. #>
[CmdletBinding()]
param(
    [ValidateSet('fashion', 'other')]
    [string]$Category = 'other',
    [ValidateRange(1, 2147483647)]
    [int]$ExpectedCount = 7,
    [string]$PythonPath,
    [switch]$CheckEnvironment,
    [string[]]$SyntheticPerformerImages,
    [ValidateSet('desktop', 'mobile')]
    [string]$AplusLayout,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Images
)

$ErrorActionPreference = 'Stop'
$candidates = @()
if ($PythonPath) {
    $candidates += [pscustomobject]@{ Command = $PythonPath; Prefix = @() }
} else {
    foreach ($commandName in @('python', 'python3', 'py')) {
        $command = Get-Command $commandName -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command -and $command.Source -notmatch '[\\/]Microsoft[\\/]WindowsApps[\\/]') {
            $prefix = @()
            if ($commandName -eq 'py') { $prefix = @('-3') }
            $candidates += [pscustomobject]@{ Command = $command.Source; Prefix = $prefix }
        }
    }
    # Known desktop bundle location; a tool-provided -PythonPath takes precedence.
    if ($env:USERPROFILE) {
        $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $bundledPython -PathType Leaf) {
            $candidates += [pscustomobject]@{ Command = $bundledPython; Prefix = @() }
        }
    }
}

# Single quotes inside Python survive Windows PowerShell's legacy native argument passing.
$probeCode = "import json,sys,PIL; from PIL import Image,ImageOps,ImageCms; ImageCms.createProfile('sRGB'); print(json.dumps({'status':'ready','python':sys.executable,'version':sys.version.split()[0],'pillow':PIL.__version__}))"
$selected = $null
$environment = $null
$diagnostics = @()
foreach ($candidate in $candidates) {
    try {
        $probeArgs = @($candidate.Prefix) + @('-B', '-X', 'utf8', '-c', $probeCode)
        $probeOutput = @(& $candidate.Command @probeArgs 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $diagnostics += "$($candidate.Command): dependency probe failed"
            continue
        }
        $environment = ($probeOutput -join "`n") | ConvertFrom-Json
        if ($environment.status -eq 'ready') {
            $selected = $candidate
            break
        }
    } catch {
        $diagnostics += "$($candidate.Command): $($_.Exception.Message)"
    }
}
if (-not $selected) {
    [Console]::Error.WriteLine('No working Python with Pillow/ImageCms was found. Use load_workspace_dependencies and supply its Python path with -PythonPath. No dependencies were installed.')
    foreach ($diagnostic in $diagnostics) { [Console]::Error.WriteLine($diagnostic) }
    exit 2
}
if ($CheckEnvironment) {
    $environment | ConvertTo-Json -Compress
    exit 0
}
if (-not $Images -or $Images.Count -eq 0) {
    [Console]::Error.WriteLine('Supply the selected image paths, or use -CheckEnvironment for an environment-only check.')
    exit 2
}
$scriptPath = Join-Path $PSScriptRoot 'verify_images.py'
$auditArgs = @($selected.Prefix) + @('-B', '-X', 'utf8', $scriptPath, '--category', $Category, '--expected-count', [string]$ExpectedCount)
if ($AplusLayout) { $auditArgs += @('--aplus-layout', $AplusLayout) }
foreach ($performerImage in $SyntheticPerformerImages) { $auditArgs += @('--synthetic-performer', $performerImage) }
$auditArgs += @('--') + @($Images)
& $selected.Command @auditArgs
exit $LASTEXITCODE
