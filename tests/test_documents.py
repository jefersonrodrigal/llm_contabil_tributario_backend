import csv
import io
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
import pytest
from docx import Document as DocxDocument

from documents import storage
from documents.extraction import (
    extract_document_text,
    formato_por_extensao,
)


def test_formato_por_extensao():
    assert formato_por_extensao("relatorio.PDF") == "pdf"
    assert formato_por_extensao("planilha.xlsx") == "xlsx"
    assert formato_por_extensao("sem_extensao") == ""


def test_extract_document_text_docx(tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Nota fiscal nº 123 — valor R$ 1.000,00")
    path = tmp_path / "doc.docx"
    doc.save(str(path))

    text = extract_document_text(path, "docx")
    assert "Nota fiscal" in text


def test_extract_document_text_xlsx(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lançamentos"
    ws.append(["Data", "Conta", "Valor"])
    ws.append(["01/01/2026", "Caixa", 1500])
    path = tmp_path / "planilha.xlsx"
    wb.save(str(path))

    text = extract_document_text(path, "xlsx")
    assert "Lançamentos" in text
    assert "Caixa" in text


def test_extract_document_text_csv(tmp_path):
    path = tmp_path / "dados.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["conta", "valor"])
        writer.writerow(["receita", "5000"])

    text = extract_document_text(path, "csv")
    assert "receita" in text
    assert "5000" in text


def test_extract_document_text_xml(tmp_path):
    root = ET.Element("nfe")
    valor = ET.SubElement(root, "valorTotal")
    valor.text = "2500.00"
    path = tmp_path / "nota.xml"
    ET.ElementTree(root).write(str(path), encoding="utf-8")

    text = extract_document_text(path, "xml")
    assert "2500.00" in text


def test_extract_document_text_formato_invalido(tmp_path):
    path = tmp_path / "arquivo.exe"
    path.write_bytes(b"binario")
    with pytest.raises(ValueError):
        extract_document_text(path, "exe")


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "documents_storage_dir", tmp_path / "documents")
    yield


def test_save_upload_txt_processa_com_sucesso(temp_storage):
    record = storage.save_upload("contrato.txt", "Contrato de prestação de serviços.".encode())
    assert record.status == "processado"
    assert record.extracted_chars > 0
    assert "Contrato" in record.text_preview


def test_save_upload_formato_invalido_marca_erro(temp_storage):
    record = storage.save_upload("virus.exe", b"conteudo binario qualquer")
    assert record.status == "erro"
    assert record.error_message is not None


def test_list_get_delete_document(temp_storage):
    record = storage.save_upload("nota.txt", "Nota fiscal de serviço.".encode())

    listed = storage.list_documents()
    assert len(listed) == 1
    assert listed[0].id == record.id

    fetched = storage.get_document(record.id)
    assert fetched is not None
    assert fetched.filename == "nota.txt"

    text = storage.get_document_text(record.id)
    assert text == "Nota fiscal de serviço."

    assert storage.delete_document(record.id) is True
    assert storage.get_document(record.id) is None
    assert storage.delete_document(record.id) is False


def test_update_analysis(temp_storage):
    record = storage.save_upload("nota.txt", "Nota fiscal.".encode())
    updated = storage.update_analysis(record.id, "Resumo da análise.", None)
    assert updated is not None
    assert updated.analysis == "Resumo da análise."

    fetched = storage.get_document(record.id)
    assert fetched.analysis == "Resumo da análise."
