from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from app.config import DEFAULT_DB_PATH, ensure_data_dirs


def get_engine(db_path: Path | str = DEFAULT_DB_PATH):
    ensure_data_dirs()
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)


def get_session(db_path: Path | str = DEFAULT_DB_PATH) -> Session:
    return Session(get_engine(db_path))

