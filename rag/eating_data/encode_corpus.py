#!/usr/bin/env python3
# encode_corpus.py
import argparse, os, re, json, hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

# Select embeddings: OpenAI if key present, else HF local
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("RAG_FORCE_LOCAL","0").lower() not in ("1","true")
if USE_OPENAI:
    from langchain_openai import OpenAIEmbeddings
    EMBED = OpenAIEmbeddings(model="text-embedding-3-small")   # 1536-d
    EMBED_FAMILY = "openai:text-embedding-3-small"
else:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBED = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384-d
    EMBED_FAMILY = "hf:sentence-transformers/all-MiniLM-L6-v2"

# ---------- helpers ----------
def clean_text(s: str) -> str:
    import re
    s = s.replace("\xa0"," ")
    s = re.sub(r"[ \t]+"," ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def sha1_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_html(path: Path) -> BeautifulSoup:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        return BeautifulSoup(text, "lxml")
    except Exception:
        return BeautifulSoup(text, "html.parser")

# ---------- textbook chunking ----------
CHAPTER_RE = re.compile(r"^\s*chapter\s+(\d+)\b[:.\s]*(.*)$", re.I)

def html_to_textbook_docs(html_path: Path, book_title: str, *, target_words=300) -> List[Document]:
    soup = read_html(html_path)
    # strip non-content
    for tag in soup(["script","style","noscript"]): tag.decompose()

    # find chapter anchors: prefer h1/h2 that look like “Chapter N …”
    sections: List[Tuple[int,str,str]] = []  # (chapter_num, chapter_title, body_text)
    heads = soup.select("h1, h2, h3")
    current = None  # (ch_num, ch_title, [parts])
    for h in heads:
        line = h.get_text(" ", strip=True)
        m = CHAPTER_RE.match(line)
        if m:
            # flush previous
            if current and current[2]:
                sections.append((current[0], current[1], clean_text("\n".join(current[2]))))
            ch_num = int(m.group(1))
            ch_title = (m.group(2) or "").strip() or f"Chapter {ch_num}"
            current = (ch_num, ch_title, [])
        elif current:
            # collect content until next chapter head
            for sib in h.find_all_next():
                if sib.name in ("h1","h2","h3") and CHAPTER_RE.match(sib.get_text(" ", strip=True)):
                    break
                if sib.name in ("p","li","pre","code","blockquote","td","th"):
                    current[2].append(sib.get_text(" ", strip=True))
            # we broke too late; stop outer after fill
            break

    # Fallback: if no explicit heads matched, treat whole body as chapter 1
    if not sections:
        body_txt = clean_text(soup.get_text("\n", strip=True))
        if body_txt:
            sections = [(1, "Chapter 1", body_txt)]
    elif current and current[2]:
        sections.append((current[0], current[1], clean_text("\n".join(current[2]))))

    docs: List[Document] = []
    for ch_num, ch_title, txt in sections:
        words = txt.split()
        step = max(180, target_words)
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i+step]).strip()
            if not piece: continue
            meta = {
                "source_type": "textbook",
                "book_title": book_title,
                "chapter": ch_num,
                "chapter_title": ch_title,
                "source": html_path.name,
                "chunk": i // step,
            }
            docs.append(Document(page_content=piece, metadata=meta))
    return docs

# ---------- slides chunking (per slide div or headings) ----------
SLIDE_ID_PAT = re.compile(r'^page(\d+)-div$', re.I)
def html_to_slide_docs(html_path: Path, course_id: str, deck_title: Optional[str]=None, *, target_words=320) -> List[Document]:
    soup = read_html(html_path)
    docs: List[Document] = []
    # case: pdftohtml per-slide divs
    divs = []
    for d in soup.find_all("div", id=True):
        m = SLIDE_ID_PAT.match(d.get("id",""))
        if m:
            divs.append((int(m.group(1)), d))
    if divs:
        divs.sort(key=lambda t: t[0])
        for num, d in divs:
            txt = clean_text(d.get_text("\n", strip=True))
            if not txt: continue
            docs.append(Document(
                page_content=txt,
                metadata={
                    "source_type": "slides",
                    "course_id": course_id,
                    "deck_title": deck_title or html_path.stem,
                    "slide": num,
                    "source": html_path.name
                }
            ))
        return docs
    # fallback: headings → paragraphs
    for h in soup.select("h1,h2,h3"):
        title = h.get_text(" ", strip=True) or html_path.stem
        buf=[]
        for sib in h.find_all_next():
            if sib.name in ("h1","h2","h3"): break
            if sib.name in ("p","li","pre","code","blockquote","td","th"):
                buf.append(sib.get_text(" ", strip=True))
        txt = clean_text("\n".join(buf))
        words = txt.split()
        for i in range(0, len(words), target_words):
            piece = " ".join(words[i:i+target_words]).strip()
            if not piece: continue
            docs.append(Document(page_content=piece, metadata={
                "source_type":"slides","course_id":course_id,
                "deck_title": deck_title or html_path.stem,
                "heading": title, "chunk": i//target_words, "source": html_path.name
            }))
    if not docs:
        body = clean_text(soup.get_text("\n", strip=True))
        if body:
            docs.append(Document(page_content=body, metadata={
                "source_type":"slides","course_id":course_id,
                "deck_title": deck_title or html_path.stem, "source": html_path.name
            }))
    return docs

def save_manifest(index_dir: Path, items: List[Path]):
    man = {
        "embed_family": EMBED_FAMILY,
        "files": {p.name: {"sha1": sha1_file(p)} for p in items}
    }
    (index_dir / "manifest.json").write_text(json.dumps(man, indent=2))

def gather_htmls(root: Path) -> List[Path]:
    if root.is_file() and root.suffix.lower() in {".html",".htm"}:
        return [root]
    return sorted([p for p in root.rglob("*.html")])

def main():
    ap = argparse.ArgumentParser(description="Encode textbooks + slides HTML into one FAISS index with chapter/slide metadata.")
    ap.add_argument("--textbooks_dir", required=True, help="Folder containing textbook HTML files")
    ap.add_argument("--slides_dir", required=True, help="Folder containing slide deck HTML files")
    ap.add_argument("--index_dir", required=True, help="Output FAISS directory")
    ap.add_argument("--course_id", required=True, help="Course id, e.g., CSC225")
    ap.add_argument("--algorithms_book_title", default="Algorithms (Goodrich & Tamassia)")
    ap.add_argument("--discrete_book_title", default="Discrete & Combinatorial Mathematics")
    ap.add_argument("--fresh", action="store_true", help="Rebuild index from scratch")
    args = ap.parse_args()

    idx_dir = Path(args.index_dir)
    if args.fresh and idx_dir.exists():
        import shutil; shutil.rmtree(idx_dir, ignore_errors=True)
    idx_dir.mkdir(parents=True, exist_ok=True)

    # Heuristic: decide book title per file name
    tb_dir = Path(args.textbooks_dir)
    tb_files = gather_htmls(tb_dir)
    slide_files = gather_htmls(Path(args.slides_dir))

    all_docs: List[Document] = []

    for p in tb_files:
        name = p.name.lower()
        if "goodrich" in name or "algorithms" in name:
            bt = args.algorithms_book_title
        elif "discrete" in name or "combinatorial" in name:
            bt = args.discrete_book_title
        else:
            bt = p.stem
        all_docs.extend(html_to_textbook_docs(p, bt))

    for p in slide_files:
        all_docs.extend(html_to_slide_docs(p, args.course_id, deck_title=p.stem))

    if not all_docs:
        raise SystemExit("No documents to index.")

    # Build FAISS (batch to avoid oversized embed requests)
    BATCH = 64
    if (idx_dir / "index.faiss").exists():
        vs = FAISS.load_local(idx_dir.as_posix(), EMBED, allow_dangerous_deserialization=True)
        for i in range(0, len(all_docs), BATCH):
            vs.add_documents(all_docs[i:i+BATCH], embedding=EMBED)
        vs.save_local(idx_dir.as_posix())
    else:
        head = all_docs[:BATCH]
        tail = all_docs[BATCH:]
        vs = FAISS.from_documents(head, EMBED)
        for i in range(0, len(tail), BATCH):
            vs.add_documents(tail[i:i+BATCH], embedding=EMBED)
        vs.save_local(idx_dir.as_posix())

    save_manifest(idx_dir, tb_files + slide_files)
    print(f"[done] docs: {len(all_docs)} | index: {idx_dir} | embed_family: {EMBED_FAMILY}")

if __name__ == "__main__":
    main()
