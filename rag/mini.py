#!/usr/bin/env python3
import json, os, re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).with_suffix(".env")) or load_dotenv()

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever

from quiz import make_quiz

# ---------------- CONFIG ----------------
INDEX_DIR = Path("./eating_data/faiss_course")
TOP_K = 6
OPENAI_CHAT_MODEL = "gpt-4o-mini"
# ---------------------------------------

from langchain_openai import ChatOpenAI
def get_llm():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return ChatOpenAI(model=OPENAI_CHAT_MODEL, temperature=0)

def _emb_from_family(family: str):
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
    if not mpath.exists(): return None
    try: return json.loads(mpath.read_text())
    except Exception: return None

def load_index():
    if not INDEX_DIR.exists():
        raise FileNotFoundError(f"Index not found at {INDEX_DIR} (run encode_corpus.py).")
    man = _load_manifest(INDEX_DIR)
    if man and "embed_family" in man:
        emb, exp_dim = _emb_from_family(man["embed_family"])
    else:
        from langchain_openai import OpenAIEmbeddings
        emb, exp_dim = OpenAIEmbeddings(model="text-embedding-3-small"), 1536
    vs = FAISS.load_local(INDEX_DIR.as_posix(), emb, allow_dangerous_deserialization=True)
    if getattr(vs.index, "d", None) != exp_dim:
        raise RuntimeError("FAISS dimension mismatch; rebuild with matching embeddings.")
    return vs

# --- Plain Q&A chain (context-only answers) ---
def build_qa_chain(vs, retriever=None):
    if retriever is None:
        retriever = vs.as_retriever(search_kwargs={"k": TOP_K})
    prompt = ChatPromptTemplate.from_template(
        "You are a helpful TA. Use ONLY the context to answer.\n"
        "If the answer isn't in the context, say you don't know.\n\n"
        "Question: {question}\n\nContext:\n{context}\n\n"
        "Answer concisely. Cite slide or chapter when available."
    )
    def fmt(docs):
        parts=[]
        for d in docs:
            m=d.metadata
            cite = ""
            if m.get("source_type")=="textbook" and "chapter" in m:
                cite=f"[{m.get('book_title','textbook')} ch {m['chapter']}]"
            elif m.get("source_type")=="slides" and "slide" in m:
                cite=f"[{m.get('deck_title','slides')} slide {m['slide']}]"
            else:
                cite=f"[{m.get('source','source')}]"
            parts.append(f"{cite} {d.page_content.strip()}")
        return "\n---\n".join(parts)
    llm = get_llm()
    return (RunnableParallel({"docs": retriever, "question": RunnablePassthrough()})
            | {"context": lambda x: fmt(x["docs"]), "question": lambda x: x["question"]}
            | prompt | llm | StrOutputParser())

# --- Quiz request parsing ---
CH_RANGE = re.compile(r"chapters?\s+(\d+)\s*[-–]\s*(\d+)", re.I)
CH_SINGLE = re.compile(r"chapter\s+(\d+)\b", re.I)

def parse_quiz_filters(text: str):
    text_l = text.lower()
    # crude book detection
    book = None
    if "algorithm" in text_l or "goodrich" in text_l or "tamassia" in text_l:
        book = "algorithms"
    elif "discrete" in text_l or "combinator" in text_l:
        book = "discrete"

    # chapter range/single
    chapters = set()
    m = CH_RANGE.search(text_l)
    if m:
        a,b = int(m.group(1)), int(m.group(2))
        for c in range(min(a,b), max(a,b)+1): chapters.add(c)
    else:
        m2 = CH_SINGLE.search(text_l)
        if m2: chapters.add(int(m2.group(1)))

    return {"book": book, "chapters": chapters}

def subset_docs(all_docs, *, book=None, chapters=set()):
    def ok(d):
        m = d.metadata
        if book:
            bt = (m.get("book_title","").lower())
            if book=="algorithms" and "algorithm" not in bt and "goodrich" not in bt and "tamassia" not in bt:
                return False
            if book=="discrete" and "discrete" not in bt and "combinatorial" not in bt:
                return False
        if chapters:
            if m.get("source_type")!="textbook": return False
            if int(m.get("chapter", -1)) not in chapters: return False
        return True
    return [d for d in all_docs if ok(d)]


def build_hybrid_retriever_for_subset(vs, subset, *, k=TOP_K):
    # BM25 over the subset
    bm25 = BM25Retriever.from_documents(subset)
    bm25.k = max(8, k)

    # stable identity for subset docs
    def meta_key(d):
        m = d.metadata
        return (m.get("source"), m.get("chunk"), m.get("slide"), m.get("chapter"))

    subset_keys = {meta_key(d) for d in subset}

    # Dense retriever constrained to subset
    class DenseSubsetRetriever(BaseRetriever):
        vs: Any
        subset_keys: set
        k: int = 8  # <-- neutral default; overridden at init

        def _get_relevant_documents(self, query: str, *, run_manager=None):
            hits = self.vs.similarity_search(query, k=max(12, 3 * self.k))
            kept = [h for h in hits if meta_key(h) in self.subset_keys]
            return kept[: self.k]

    dense = DenseSubsetRetriever(vs=vs, subset_keys=subset_keys, k=max(8, k))

    # Hybrid retriever
    return EnsembleRetriever(retrievers=[bm25, dense], weights=[0.5, 0.5])


def main():
    vs = load_index()
    all_docs = list(vs.docstore._dict.values())
    print(f"[diag] loaded {len(all_docs)} chunks from {len({d.metadata.get('source') for d in all_docs})} files")

    # Default hybrid (whole corpus)
    bm25_all = BM25Retriever.from_documents(all_docs); bm25_all.k = max(8, TOP_K)
    dense_all = vs.as_retriever(search_kwargs={"k": max(8, TOP_K)})
    hybrid_all = EnsembleRetriever(retrievers=[bm25_all, dense_all], weights=[0.4, 0.6])

    qa_chain = build_qa_chain(vs, retriever=hybrid_all)
    llm = get_llm()

    print("\nReady. Ask anything, or try:\n  /quiz algorithms chapters 1-3 n=8\n  /quiz discrete chapter 2 n=5\n(Ctrl+C to exit)\n")

    try:
        while True:
            q = input("\nQ> ").strip()
            if not q: continue

            if q.startswith("/quiz"):
                # parse topic text after '/quiz'
                topic_text = q.replace("/quiz","",1).strip()
                # optional n=
                m_n = re.search(r"\bn=(\d+)", topic_text)
                n = int(m_n.group(1)) if m_n else 10
                topic_text = re.sub(r"\bn=\d+\b", "", topic_text).strip()

                f = parse_quiz_filters(topic_text)
                subset = subset_docs(all_docs, book=f["book"], chapters=f["chapters"])
                if not subset:
                    print("\nA> Sorry, I couldn't find matching chapters/books in the corpus.\n")
                    continue

                filt_retriever = build_hybrid_retriever_for_subset(vs, subset, k=TOP_K)
                title_bits=[]
                if f["book"]=="algorithms": title_bits.append("Algorithms")
                if f["book"]=="discrete": title_bits.append("Discrete Math")
                if f["chapters"]: title_bits.append("Ch " + "-".join(map(str,sorted(f["chapters"]))))
                title = " ".join(title_bits) + " Quiz" if title_bits else "Course Quiz"

                quiz = make_quiz(filt_retriever, llm, topic=topic_text or "course material", n=n, title=title)
                print("\nA> ", quiz.model_dump_json(indent=2), "\n")
                continue

            # normal QA
            ans = qa_chain.invoke(q)
            print(f"\nA> {ans}\n")
    except KeyboardInterrupt:
        print("\nbye!")

if __name__ == "__main__":
    main()
