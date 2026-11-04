"""Extração de texto de documentos enviados pelo usuário (Fase 7): PDF,
DOCX, XLSX, CSV e XML. PDF reaproveita ai_engine.extraction (via a fachada
ai_engine.client); os demais formatos são específicos deste módulo (a base
de legislação não usa esses tipos)."""
import csv
import io
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
from docx import Document as DocxDocument

from ai_engine.client import extract_text_from_pdf

FORMATOS_SUPORTADOS = {"pdf", "docx", "xlsx", "csv", "xml", "txt"}


def formato_por_extensao(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext


def extract_text_from_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    partes = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            linha = " | ".join(cell.text.strip() for cell in row.cells)
            if linha.strip(" |"):
                partes.append(linha)
    return "\n".join(partes)


def extract_text_from_xlsx(path: Path) -> str:
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    linhas = []
    for sheet in wb.worksheets:
        linhas.append(f"[Planilha: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            valores = [str(v) for v in row if v is not None]
            if valores:
                linhas.append(" | ".join(valores))
    wb.close()
    return "\n".join(linhas)


def extract_text_from_csv(path: Path) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return "\n".join(" | ".join(row) for row in reader if row)


def extract_text_from_xml(path: Path) -> str:
    tree = ET.parse(str(path))
    textos = [elem.text.strip() for elem in tree.iter() if elem.text and elem.text.strip()]
    return "\n".join(textos)


def extract_text_from_txt(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def extract_document_text(path: Path, formato: str) -> str:
    if formato not in FORMATOS_SUPORTADOS:
        raise ValueError(f"Formato não suportado: {formato}")
    if formato == "pdf":
        return extract_text_from_pdf(path)
    if formato == "docx":
        return extract_text_from_docx(path)
    if formato == "xlsx":
        return extract_text_from_xlsx(path)
    if formato == "csv":
        return extract_text_from_csv(path)
    if formato == "xml":
        return extract_text_from_xml(path)
    return extract_text_from_txt(path)
