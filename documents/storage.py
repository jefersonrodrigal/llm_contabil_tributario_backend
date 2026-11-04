"""Persistência local de documentos enviados pelo usuário (Fase 7).

Sem backend Java/banco de dados ainda: os arquivos e um índice de metadados
(JSON) ficam em disco, em `database/documents/`. Isso sobrevive a reinícios
do backend, mas não tem controle de acesso por usuário/empresa (não existe
autenticação), nem é seguro para escritas concorrentes de múltiplos
processos — aceitável para uma instância local de desenvolvimento, não para
produção multiusuário.
"""
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from documents.extraction import extract_document_text, formato_por_extensao

PREVIEW_CHARS = 500


@dataclass
class DocumentRecord:
    id: str
    filename: str
    formato: str
    size_bytes: int
    uploaded_at: str
    status: str  # "processado" | "erro"
    error_message: str | None = None
    extracted_chars: int = 0
    text_preview: str = ""
    analysis: str | None = None
    analysis_error: str | None = None


def _files_dir() -> Path:
    path = settings.documents_storage_dir / "files"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extracted_dir() -> Path:
    path = settings.documents_storage_dir / "extracted"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path() -> Path:
    settings.documents_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings.documents_storage_dir / "index.json"


def _load_index() -> list[dict]:
    path = _index_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(records: list[dict]) -> None:
    _index_path().write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def save_upload(filename: str, content: bytes) -> DocumentRecord:
    doc_id = str(uuid.uuid4())
    formato = formato_por_extensao(filename)
    file_path = _files_dir() / f"{doc_id}.{formato}"
    file_path.write_bytes(content)

    record = DocumentRecord(
        id=doc_id,
        filename=filename,
        formato=formato,
        size_bytes=len(content),
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        status="processado",
    )

    try:
        text = extract_document_text(file_path, formato)
        (_extracted_dir() / f"{doc_id}.txt").write_text(text, encoding="utf-8")
        record.extracted_chars = len(text)
        record.text_preview = text[:PREVIEW_CHARS]
        record.status = "processado" if text.strip() else "erro"
        if not text.strip():
            record.error_message = "Nenhum texto extraído do documento."
    except Exception as exc:  # noqa: BLE001 — formatos externos podem falhar de várias formas
        record.status = "erro"
        record.error_message = str(exc)

    records = _load_index()
    records.insert(0, asdict(record))
    _save_index(records)
    return record


def list_documents() -> list[DocumentRecord]:
    return [DocumentRecord(**r) for r in _load_index()]


def get_document(doc_id: str) -> DocumentRecord | None:
    for r in _load_index():
        if r["id"] == doc_id:
            return DocumentRecord(**r)
    return None


def get_document_text(doc_id: str) -> str | None:
    path = _extracted_dir() / f"{doc_id}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def delete_document(doc_id: str) -> bool:
    records = _load_index()
    remaining = [r for r in records if r["id"] != doc_id]
    if len(remaining) == len(records):
        return False
    _save_index(remaining)

    doc = next((r for r in records if r["id"] == doc_id), None)
    if doc:
        file_path = _files_dir() / f"{doc_id}.{doc['formato']}"
        file_path.unlink(missing_ok=True)
        (_extracted_dir() / f"{doc_id}.txt").unlink(missing_ok=True)
    return True


def update_analysis(doc_id: str, analysis: str | None, error: str | None) -> DocumentRecord | None:
    records = _load_index()
    for r in records:
        if r["id"] == doc_id:
            r["analysis"] = analysis
            r["analysis_error"] = error
            _save_index(records)
            return DocumentRecord(**r)
    return None
