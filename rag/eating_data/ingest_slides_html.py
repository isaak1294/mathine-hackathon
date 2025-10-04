#!/usr/bin/env python3
import os, re, argparse, hashlib, json
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# ---- Embedding provider must match mini.py ----
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("RAG_FORCE_LOCAL","0").lower() not in ("1","true")
if USE_OPENAI:
    from langchain_openai import OpenAIEmbeddings
    EMBED = OpenAIEmbeddings(model="text-embedding-3-small")  # 1536-d
    EMBED_FAMILY = "openai:text-embedding-3-small"
else:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBED = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384-d
    EMBED_FAMILY = "hf:all-MiniLM-L6-v2"

# accept multiple pdftohtml flavors
SLIDE_ID_PATTERNS = (
    re.compile(r'^page(\d+)-div$', re.I),   # page1-div
    re.compile(r'^page\s*(\d+)$', re.I),    # page1
)
SLIDE_CLASS_HINTS = ("pc",)  # some tools add <div class="pc" data-page-no="1">

def h8(s: str) -> str:
    return hashlib.blake2b(s.encode("utf-8"), digest_size=8).hexdigest()

def file_sha1(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def find_slide_number(div) -> int | None:
    # try id patterns
    div_id = (div.get("id") or "").strip()
    for pat in SLIDE_ID_PATTERNS:
        m = pat.match(div_id)
        if m:
            return int(m.group(1))
    # try class-based hint with data attribute
    cls = div.get("class") or []
    if any(c in SLIDE_CLASS_HINTS for c in cls):
        # many generators add data-page-no
        dpn = div.get("data-page-no")
        if dpn and dpn.isdigit():
            return int(dpn)
    return None

def html_to_slide_docs(html_path: Path, course_id: str, version: str) -> List[Document]:
    # lxml parser is faster/more robust if installed; falls back to html.parser
    try:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    except Exception:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")

    docs: List[Document] = []

    # Case A: one block per slide
    slide_blocks: list[tuple[int, str]] = []
    for div in soup.find_all("div"):
        sn = find_slide_number(div)
        if sn is not None:
            text = clean_text(div.get_text(separator="\n", strip=True))
            if text:
                slide_blocks.append((sn, text))

    if slide_blocks:
        slide_blocks.sort(key=lambda t: t[0])
        for slide_num, text in slide_blocks:
            docs.append(Document(
                page_content=text,
                metadata={
                    "course_id": course_id,
                    "version": version,
                    "doc_type": "lecture_slide",
                    "source": html_path.name,
                    "slide": slide_num,
                    "chunk_id": h8(f"{course_id}|{version}|{html_path.name}|slide:{slide_num}|{text[:200]}"),
                },
            ))
        return docs

    # Case B: fallback — chunk by headings, then paragraphs
    sections = []
    for h in soup.select("h1, h2, h3"):
        title = h.get_text(" ", strip=True)
        content = []
        for sib in h.find_all_next():
            if sib.name in ("h1", "h2", "h3"):
                break
            if sib.name in ("p","li","pre","code","blockquote","td","th"):
                content.append(sib.get_text(" ", strip=True))
        txt = clean_text("\n".join(content))
        if txt:
            sections.append((title, txt))

    if not sections:
        body_txt = clean_text(soup.get_text("\n", strip=True))
        if body_txt:
            sections = [("body", body_txt)]

    step_words = 350
    for title, txt in sections:
        words = txt.split()
        for i in range(0, len(words), step_words):
            piece = " ".join(words[i:i+step_words]).strip()
            if not piece:
                continue
            docs.append(Document(
                page_content=piece,
                metadata={
                    "course_id": course_id,
                    "version": version,
                    "doc_type": "lecture_slide",
                    "source": html_path.name,
                    "heading": title,
                    "chunk": i // step_words,
                    "chunk_id": h8(f"{course_id}|{version}|{html_path.name}|{title}|{i}|{piece[:200]}"),
                },
            ))
    return docs

def main():
    ap = argparse.ArgumentParser(description="Ingest HTML slide decks into a FAISS index.")
    ap.add_argument("--input_dir", required=True, help="Folder containing HTML slide files")
    ap.add_argument("--course_id", required=True, help="Course id, e.g., CSC225")
    ap.add_argument("--version", required=True, help="Version/term, e.g., 2025-09-01")
    ap.add_argument("--index_dir", default="./faiss_course_index", help="Where to store FAISS")
    ap.add_argument("--glob", default="*.html", help="Pattern for slide files")
    ap.add_argument("--fresh", action="store_true", help="Rebuild index from scratch")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    index_dir = Path(args.index_dir)
    htmls = sorted(input_dir.glob(args.glob))
    if not htmls:
        raise SystemExit(f"No HTML files matching {args.glob} in {input_dir}")

    if args.fresh and index_dir.exists():
        import shutil
        shutil.rmtree(index_dir, ignore_errors=True)

    # Simple change-detection (skip unchanged files if appending)
    manifest_path = index_dir / "manifest.json"
    old_manifest = {}
    if index_dir.exists() and manifest_path.exists():
        try:
            old_manifest = json.loads(manifest_path.read_text())
        except Exception:
            old_manifest = {}

    to_ingest = []
    new_manifest = {"embed_family": EMBED_FAMILY, "files": {}}
    for p in htmls:
        sha = file_sha1(p)
        new_manifest["files"][p.name] = {"sha1": sha}
        if not index_dir.exists() or old_manifest.get("files", {}).get(p.name, {}).get("sha1") != sha:
            to_ingest.append(p)

    if not index_dir.exists() or args.fresh:
        to_ingest = htmls  # full rebuild

    all_docs: List[Document] = []
    for p in to_ingest:
        all_docs.extend(html_to_slide_docs(p, args.course_id, args.version))

    print(f"Ingesting {len(all_docs)} chunks from {len(to_ingest)} files "
          f"(total files in dir: {len(htmls)})…")

    if index_dir.exists():
        vs = FAISS.load_local(index_dir.as_posix(), EMBED, allow_dangerous_deserialization=True)
        if all_docs:
            vs.add_documents(all_docs, embedding=EMBED)
            vs.save_local(index_dir.as_posix())
    else:
        vs = FAISS.from_documents(all_docs or [Document(page_content="", metadata={})], EMBED)
        vs.save_local(index_dir.as_posix())

    # Save/refresh manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(new_manifest, indent=2))

    print(f"Saved FAISS index to {index_dir}")
    print(f"Embed family: {EMBED_FAMILY}")
    print(f"Files tracked: {len(new_manifest['files'])}")

if __name__ == "__main__":
    main()
