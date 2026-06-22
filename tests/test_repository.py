from app.storage.models import GuidanceDocument
from app.storage.repository import GuidanceRepository, stable_document_id


def make_document(summary: str = "Initial summary") -> GuidanceDocument:
    return GuidanceDocument(
        title="Example Biostatistics Guidance",
        agency="FDA",
        jurisdiction="US",
        source_page_url="https://www.fda.gov/example",
        status_normalized="final",
        topic_normalized="biostatistics",
        summary=summary,
    )


def test_repository_inserts_new_record(tmp_path):
    repo = GuidanceRepository(tmp_path / "guidance.db")

    saved = repo.save(make_document())

    assert saved.id
    assert saved.change_type == "new"
    assert len(repo.list_documents()) == 1


def test_repository_marks_duplicate_as_unchanged(tmp_path):
    repo = GuidanceRepository(tmp_path / "guidance.db")
    repo.save(make_document())

    saved = repo.save(make_document())

    assert saved.change_type == "unchanged"
    assert len(repo.list_documents()) == 1


def test_repository_marks_changed_key_fields_as_updated(tmp_path):
    repo = GuidanceRepository(tmp_path / "guidance.db")
    repo.save(make_document())

    saved = repo.save(make_document(summary="Changed summary"))

    assert saved.change_type == "updated"
    assert len(repo.list_documents()) == 1


def test_stable_document_id_is_repeatable():
    assert stable_document_id(make_document()) == stable_document_id(make_document())

