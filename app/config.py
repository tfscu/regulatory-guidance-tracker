from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = DATA_DIR / "exports"
DEFAULT_DB_PATH = DATA_DIR / "regulatory_guidance.db"
SNAPSHOT_DIR = PROJECT_ROOT / "data_snapshots"
DEFAULT_DB_SNAPSHOT_PATH = SNAPSHOT_DIR / "regulatory_guidance_snapshot.db"
SOURCES_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"


HIGH_PRIORITY_TOPICS = {
    "biostatistics",
    "clinical_trial_design",
    "estimand_and_missing_data",
    "adaptive_design",
    "bayesian_methods",
    "master_protocol",
    "external_control",
    "real_world_evidence",
    "vaccine_development",
    "immunogenicity",
    "safety_pharmacovigilance",
}


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)


def bootstrap_database_from_snapshot(
    db_path: Path | str = DEFAULT_DB_PATH,
    snapshot_path: Path | str = DEFAULT_DB_SNAPSHOT_PATH,
) -> bool:
    path = Path(db_path)
    if path.exists():
        return False

    snapshot = Path(snapshot_path)
    if not snapshot.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot, path)
    return True


def load_sources_config(path: Path = SOURCES_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"sources": {}}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {"sources": {}}
