from app.config import bootstrap_database_from_snapshot


def test_bootstrap_database_from_snapshot_copies_missing_database(tmp_path):
    snapshot = tmp_path / "snapshots" / "regulatory_guidance_snapshot.db"
    snapshot.parent.mkdir()
    snapshot.write_bytes(b"sqlite snapshot")
    db_path = tmp_path / "data" / "regulatory_guidance.db"

    copied = bootstrap_database_from_snapshot(db_path, snapshot)

    assert copied is True
    assert db_path.read_bytes() == b"sqlite snapshot"


def test_bootstrap_database_from_snapshot_keeps_existing_database(tmp_path):
    snapshot = tmp_path / "snapshots" / "regulatory_guidance_snapshot.db"
    snapshot.parent.mkdir()
    snapshot.write_bytes(b"new snapshot")
    db_path = tmp_path / "data" / "regulatory_guidance.db"
    db_path.parent.mkdir()
    db_path.write_bytes(b"existing db")

    copied = bootstrap_database_from_snapshot(db_path, snapshot)

    assert copied is False
    assert db_path.read_bytes() == b"existing db"
