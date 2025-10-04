import json, os, re, hashlib
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).with_suffix(".env")) or load_dotenv()

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever

# ---------------- CONFIG ----------------
INDEX_DIR = Path("./eating_data/faiss_book")  # <- your slides index
TOP_K = 6
OPENAI_CHAT_MODEL = "gpt-4o-mini"
# ---------------------------------------

# --- LLM (OpenAI only) ---
from langchain_openai import ChatOpenAI
def get_llm():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Put it in .env or export it in your shell."
        )
    return ChatOpenAI(model=OPENAI_CHAT_MODEL, temperature=0)

# --- Embeddings chosen by index manifest ---
def _emb_from_family(family: str):
    """
    Map manifest 'embed_family' -> embedding instance and expected dim.
    Supports the families emitted by ingest_slides_html.py.
    """
    family = (family or "").strip().lower()
    if family == "openai:text-embedding-3-small":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small"), 1536
    if family in ("hf:all-minilm-l6-v2", "hf:sentence-transformers/all-minilm-l6-v2"):
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"), 384
    raise ValueError(f"Unknown embed_family in manifest: {family!r}")

def _load_manifest(index_dir: Path):
    mpath = index_dir / "manifest.json"
    if not mpath.exists():
        # Back-compat: no manifest (older index) — try OpenAI first, then HF on mismatch
        return None
    try:
        return json.loads(mpath.read_text())
    except Exception:
        return None

def build_or_load_index():
    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {INDEX_DIR}.\n"
            f"Run ingest first, e.g.:\n"
            f"  python3 ingest_slides_html.py --input_dir ./CSC225/SlidesHTML "
            f"--course_id CSC225 --version 2025-09-01 --index_dir {INDEX_DIR}"
        )

    manifest = _load_manifest(INDEX_DIR)
    if manifest and "embed_family" in manifest:
        emb, exp_dim = _emb_from_family(manifest["embed_family"])
    else:
        # No manifest — default to OpenAI embeddings, we’ll check dim and hint if wrong.
        from langchain_openai import OpenAIEmbeddings
        emb, exp_dim = OpenAIEmbeddings(model="text-embedding-3-small"), 1536

    vs = FAISS.load_local(INDEX_DIR.as_posix(), emb, allow_dangerous_deserialization=True)
    idx_dim = getattr(vs.index, "d", None)

    if idx_dim != exp_dim:
        hint = ""
        if manifest and "embed_family" in manifest:
            hint = f"(manifest says {manifest['embed_family']}) "
        raise RuntimeError(
            f"FAISS dimension mismatch: index={idx_dim}, expected={exp_dim}. {hint}\n"
            f"Rebuild the index with the same embedding family you intend to use:\n"
            f"  # OpenAI (1536-d)\n"
            f"  export OPENAI_API_KEY=... && unset RAG_FORCE_LOCAL\n"
            f"  python3 ingest_slides_html.py --fresh --index_dir {INDEX_DIR} --input_dir ./CSC225/SlidesHTML --course_id CSC225 --version 2025-09-01\n"
            f"  # OR HF local (384-d)\n"
            f"  export RAG_FORCE_LOCAL=1\n"
            f"  python3 ingest_slides_html.py --fresh --index_dir {INDEX_DIR} --input_dir ./CSC225/SlidesHTML --course_id CSC225 --version 2025-09-01"
        )

    return vs, emb  # emb returned in case you want to reuse it elsewhere

def build_rag_chain(vs, retriever=None):
    if retriever is None:
        retriever = vs.as_retriever(search_kwargs={"k": TOP_K})

    prompt = ChatPromptTemplate.from_template(
        "You are a helpful TA. Use ONLY the context to answer.\n"
        "If the answer isn't in the context, say you don't know.\n\n"
        "Question: {question}\n\nContext:\n{context}\n\n"
        "Answer concisely. Always cite slide numbers if present."
    )

    def fmt(docs):
        parts = []
        for d in docs:
            m = d.metadata
            src = m.get("source", "slides")
            if "slide" in m:
                cite = f"[{src} slide {m['slide']}]"
            elif "heading" in m:
                cite = f"[{src} {m.get('heading','section')}]"
            else:
                cite = f"[{src}]"
            parts.append(f"{cite} {d.page_content.strip()}")
        return "\n---\n".join(parts)

    llm = get_llm()
    return (
        RunnableParallel({"docs": retriever, "question": RunnablePassthrough()})
        | {"context": lambda x: fmt(x["docs"]), "question": lambda x: x["question"]}
        | prompt
        | llm
        | StrOutputParser()
    )

def main():
    vs, _ = build_or_load_index()

    # Diagnostics
    all_docs = list(vs.docstore._dict.values())
    print(f"[diag] loaded {len(all_docs)} chunks from {len({d.metadata.get('source') for d in all_docs})} files")

    # Hybrid retriever: BM25 + FAISS
    bm25 = BM25Retriever.from_documents(all_docs); bm25.k = max(8, TOP_K)
    dense = vs.as_retriever(search_kwargs={"k": max(8, TOP_K)})
    retriever = EnsembleRetriever(retrievers=[bm25, dense], weights=[0.4, 0.6])
    print("Retriever = EnsembleRetriever (hybrid)")

    chain = build_rag_chain(vs, retriever=retriever)

    print("\nReady. Ask about your slides. (Ctrl+C to exit)")
    try:
        while True:
            q = input("\nQ> ").strip()
            if not q:
                continue
            ans = chain.invoke(q)
            print(f"\nA> {ans}\n")
    except KeyboardInterrupt:
        print("\nbye!")

if __name__ == "__main__":
    main()
