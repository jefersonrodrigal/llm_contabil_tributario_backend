"""Interface de chat (Streamlit) para o MVP RAG contábil/tributário.

Executa a lógica de RAG + Ollama diretamente (sem passar pela API FastAPI),
para manter o MVP simples. Rodar com:
    streamlit run app/interface/streamlit_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from ai_engine.client import count as vector_count
from app.chat_service import answer_question

st.set_page_config(page_title="Assistente Contábil/Tributário", page_icon="📊")
st.title("📊 Assistente Contábil/Tributário (MVP)")

n_chunks = vector_count()
if n_chunks == 0:
    st.warning(
        "A base de conhecimento está vazia. Rode `python -m rag.ingestion` para "
        "indexar os documentos do manifesto antes de conversar."
    )
else:
    st.caption(f"Base documental: {n_chunks} trechos indexados.")

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Pergunte sobre contabilidade, tributos ou a Reforma Tributária...")
if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando a base documental e gerando resposta..."):
            try:
                result = answer_question(question)
            except RuntimeError as exc:
                st.error(str(exc))
                result = None

        if result:
            st.markdown(result.answer)
            if result.sources:
                with st.expander(f"Fontes (data de referência: {result.reference_date})"):
                    for src in result.sources:
                        artigo = f" — Art. {src['artigo']}" if src.get("artigo") else ""
                        st.markdown(
                            f"- **{src['titulo']}**{artigo} · status: `{src['status']}` · "
                            f"[fonte]({src['url_fonte']})"
                        )
            st.session_state.history.append({"role": "assistant", "content": result.answer})
