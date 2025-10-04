#!/usr/bin/env python3
"""
encode_html_to_faiss.py — turn HTML content into a FAISS index for RAG

Usage:
  # single file
  python3 encode_html_to_faiss.py --input ./out-html/book.html --index_dir ./faiss_book

  # folder of HTMLs
  python3 encode_html_to_faiss.py --input ./SlidesHTML --index_dir ./faiss_course

Env:
  OPENAI_API_KEY=...            # if set → uses OpenAI embeddings (1536-d)
  LANGCHAIN_API_KEY=...         # optional (LangSmith)
  LANGCHAIN_TRACING_V2=true     # optional (LangSmith)
"""

import argparse, os, re, json, hashlib
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

# ----- env -----
load_dotenv()

USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    from langchain_openai import OpenAIEmbeddings
    EMBED = OpenAIEmbeddings(model="text-embedding-3-small")  # 1536-d
    EMBED_FAMILY = "openai:text-embedding-3-small"
else:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBED = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384-d
    EMBED_FAMILY = "hf:sentence-transformers/all-MiniLM-L6-v2"

# ----- helpers -----
def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def html_to_docs(html_path: Path, course_id: str|None, version: str|None,
                 target_words: int = 350) -> List[Document]:
    """Chunk by headings→paragraphs; fallback to body; attach useful metadata."""
    # lxml is faster if installed; fall back to html.parser
    try:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    except Exception:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")

    docs: List[Document] = []
    sections: List[Tuple[str, str]] = []

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # grab sections under h1/h2/h3
    for h in soup.select("h1, h2, h3"):
        title = h.get_text(" ", strip=True)
        parts = []
        for sib in h.find_all_next():
            if sib.name in ("h1", "h2", "h3"):
                break
            if sib.name in ("p", "li", "pre", "code", "blockquote", "td", "th"):
                parts.append(sib.get_text(" ", strip=True))
        txt = clean_text("\n".join(parts))
        if txt:
            sections.append((title or "section", txt))

    if not sections:
        body_txt = clean_text(soup.get_text("\n", strip=True))
        if body_txt:
            sections = [("body", body_txt)]

    for title, txt in sections:
        words = txt.split()
        step = max(120, target_words)  # don’t go too small
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i+step]).strip()
            if not piece:
                continue
            meta = {
                "source": html_path.name,
                "doc_type": "html",
                "heading": title,
                "chunk": i // step,
            }
            if course_id: meta["course_id"] = course_id
            if version:   meta["version"] = version
            docs.append(Document(page_content=piece, metadata=meta))
    return docs

def load_html_inputs(input_path: Path) -> List[Path]:
    if input_path.is_file() and input_path.suffix.lower() in {".html", ".htm"}:
        return [input_path]
    if input_path.is_dir():
        return sorted([p for p in input_path.rglob("*.html")])
    raise SystemExit(f"No HTML found at {input_path}")

def save_manifest(index_dir: Path, files: List[Path]):
    man = {
        "embed_family": EMBED_FAMILY,
        "files": {p.name: {"sha1": sha1_file(p)} for p in files}
    }
    (index_dir / "manifest.json").write_text(json.dumps(man, indent=2))

# ----- main -----
def main():
    ap = argparse.ArgumentParser(description="Encode HTML files into a FAISS index for RAG.")
    ap.add_argument("--input", required=True, help="Path to an HTML file or a folder of HTML files")
    ap.add_argument("--index_dir", required=True, help="Output folder for FAISS index")
    ap.add_argument("--course_id", default=None, help="Optional course id (e.g., CSC225)")
    ap.add_argument("--version", default=None, help="Optional version/term (e.g., 2025-09-01)")
    ap.add_argument("--fresh", action="store_true", help="Rebuild index from scratch")
    ap.add_argument("--target_words", type=int, default=350, help="Chunk size in words")
    args = ap.parse_args()

    input_path = Path(args.input)
    index_dir  = Path(args.index_dir)
    htmls = load_html_inputs(input_path)
    if not htmls:
        raise SystemExit("No HTML files to encode.")

    if args.fresh and index_dir.exists():
        import shutil; shutil.rmtree(index_dir, ignore_errors=True)

    print(f"[info] embedding provider: {EMBED_FAMILY}")
    print(f"[info] encoding {len(htmls)} HTML file(s) → {index_dir}")

    # Build docs
    all_docs: List[Document] = []
    for p in htmls:
        all_docs.extend(html_to_docs(p, args.course_id, args.version, args.target_words))

    if not all_docs:
        raise SystemExit("No text extracted from HTML files.")

    # Build or append FAISS
    index_dir.mkdir(parents=True, exist_ok=True)
    BATCH = 64  # conservative; keeps total tokens per request well under 300k

    from_docs = all_docs[:BATCH]
    rest_docs = all_docs[BATCH:]

    if (index_dir / "index.faiss").exists():
        vs = FAISS.load_local(index_dir.as_posix(), EMBED, allow_dangerous_deserialization=True)
        # add in batches
        for i in range(0, len(all_docs), BATCH):
            vs.add_documents(all_docs[i:i+BATCH], embedding=EMBED)
        vs.save_local(index_dir.as_posix())
    else:
        # create index from first batch
        vs = FAISS.from_documents(from_docs, EMBED)
        # add remaining batches
        for i in range(0, len(rest_docs), BATCH):
            vs.add_documents(rest_docs[i:i+BATCH], embedding=EMBED)
        vs.save_local(index_dir.as_posix())

    save_manifest(index_dir, htmls)
    print(f"[done] chunks: {len(all_docs)} | index: {index_dir}")

if __name__ == "__main__":
    main()
