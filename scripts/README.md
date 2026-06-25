# Guidance database update script

Use `update_guidance_database.ps1` to update the local SQLite guidance database from the command line.

The script is portable across checkouts because it resolves the repository root from its own location instead of using an absolute user path.

## First run on a new computer

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -InstallDependencies -DryRun
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -InstallDependencies
```

`-InstallDependencies` runs:

```powershell
python -m pip install -e .
python -m playwright install chromium
```

## Regular update

Update all supported agencies:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1
```

Update one agency:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -Agency EMA
```

Use a specific Python executable:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -Python "C:\Path\To\python.exe"
```

## Outputs

- SQLite database: `data\regulatory_guidance.db`
- Database backups: `data\backups\`
- Run logs: `data\logs\`
- CSV export: `data\exports\regulatory_guidance.csv`
- Markdown report: `data\exports\regulatory_update_report.md`

The script backs up the current database before updating it. It does not delete old agency records before crawling, so a temporary website failure should not wipe existing records.
