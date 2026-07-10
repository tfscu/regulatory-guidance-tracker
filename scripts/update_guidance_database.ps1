param(
    [ValidateSet("all", "FDA", "EMA", "ICH", "CDE", "PMDA")]
    [string]$Agency = "all",

    [string]$Python = "python",

    [switch]$InstallDependencies,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Invoke-CommandStep {
    param(
        [string]$Description,
        [string[]]$Command
    )

    Write-Step $Description
    Write-Host ("    " + ($Command -join " "))

    if ($DryRun) {
        return
    }

    & $Command[0] @($Command[1..($Command.Length - 1)])
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed with exit code ${LASTEXITCODE}: $Description"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DataDir = Join-Path $RepoRoot "data"
$LogDir = Join-Path $DataDir "logs"
$BackupDir = Join-Path $DataDir "backups"
$DbPath = Join-Path $DataDir "regulatory_guidance.db"
$LogPath = Join-Path $LogDir "guidance_update_${Timestamp}.log"

if (-not $DryRun) {
    New-Item -ItemType Directory -Force $DataDir, $LogDir, $BackupDir | Out-Null
    Start-Transcript -Path $LogPath -Append | Out-Null
}

try {
    Write-Step "Regulatory Guidance Tracker update"
    Write-Host "Repository: $RepoRoot"
    Write-Host "Agency:     $Agency"
    Write-Host "Python:     $Python"
    Write-Host "Dry run:    $DryRun"
    if (-not $DryRun) {
        Write-Host "Log:        $LogPath"
    }

    Invoke-CommandStep "Check Python" @($Python, "--version")

    if ($InstallDependencies) {
        Invoke-CommandStep "Install Python package dependencies" @($Python, "-m", "pip", "install", "-e", ".")
        Invoke-CommandStep "Install Playwright Chromium browser" @($Python, "-m", "playwright", "install", "chromium")
    }

    Invoke-CommandStep "Check application import" @($Python, "-c", "import app.cli")

    if ((Test-Path $DbPath) -and (-not $DryRun)) {
        $BackupPath = Join-Path $BackupDir "regulatory_guidance_${Timestamp}.db"
        Write-Step "Back up current SQLite database"
        Copy-Item -LiteralPath $DbPath -Destination $BackupPath -Force
        Write-Host "Backup: $BackupPath"
    }

    Invoke-CommandStep "Initialize SQLite schema" @($Python, "-m", "app.cli", "init-db")
    Invoke-CommandStep "Crawl guidance records" @(
        $Python,
        "-m",
        "app.cli",
        "crawl",
        "--agency",
        $Agency,
        "--all-records",
        "--no-seed-if-empty"
    )
    Invoke-CommandStep "Export CSV" @($Python, "-m", "app.cli", "export-csv")
    Invoke-CommandStep "Generate Markdown report" @($Python, "-m", "app.cli", "generate-report")

    Write-Step "Update completed"
    if (-not $DryRun) {
        Write-Host "Log saved to: $LogPath"
    }
}
finally {
    if (-not $DryRun) {
        Stop-Transcript | Out-Null
    }
}
