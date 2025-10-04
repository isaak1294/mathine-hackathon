#!/usr/bin/env python3
"""
textbook_to_html.py — robust PDF (textbook) → HTML converter

Strategy (per file):
  1) pdftotext (layout → default → raw)
  2) MuPDF mutool (text)
  3) pdfminer.six
  4) pdftohtml -xml  → rebuild paragraphs from positioned <text> nodes
  5) (optional) OCR: ocrmypdf --skip-text → pdftotext
  6) Last resort: pdftohtml page images (always produces something)

Works on Ubuntu. Handles weird PDFs (e.g., ones reprocessed by iLovePDF) that render
but have unusable ToUnicode maps.

Usage:
  python3 textbook_to_html.py INPUT_PATH --out-dir ./out-html [--enable-ocr] [--workers 8]
  - INPUT_PATH can be a single PDF file or a directory of PDFs.
"""

from __future__ import annotations
import argparse
import concurrent.futures as cf
import html
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# ----------------------- helpers -----------------------

def run(cmd: str) -> subprocess.CompletedProcess:
    """Run a shell command and return CompletedProcess, raising on non-zero."""
    return subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

def try_run(cmd: str) -> Optional[subprocess.CompletedProcess]:
    """Run but don't raise; return None on failure."""
    try:
        return run(cmd)
    except subprocess.CalledProcessError:
        return None

def which(name: str) -> Optional[str]:
    res = subprocess.run(f"command -v {shlex.quote(name)}", shell=True, stdout=subprocess.PIPE)
    p = res.stdout.decode().strip()
    return p or None

def require(tool: str, soft: bool=False):
    if which(tool): return
    msg = f"[warn] Missing tool: {tool}"
    if soft:
        print(msg)
    else:
        print(msg)
        sys.exit(1)

def safe_stem(path: Path) -> str:
    # cleaner stem for odd filenames
    stem = path.stem.strip().replace(" ", "_")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem)
    return stem[:120] or "file"

def write_html(text: str, title: str) -> str:
    import html as _html
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    def _sanitize(p: str) -> str:
        s = _html.escape(p)
        s = s.replace("  ", "&nbsp;&nbsp;")
        s = s.replace("\n", "<br/>")
        return s

    body = "\n".join("<p>{}</p>".format(_sanitize(p)) for p in paras)

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        f"<title>{_html.escape(title)}</title>\n"
        "<meta name=\"generator\" content=\"textbook_to_html.py\"/>\n"
        "<style>\n"
        "  body{margin:2rem auto;max-width:900px;line-height:1.55;"
        "font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}\n"
        "  p{margin:0 0 0.9rem}\n"
        "</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>"
    )

# ----------------------- XML → paragraphs -----------------------

def xml_to_html_paragraphs(xml_path: Path, title: str) -> str:
    """
    Rebuild paragraphs from pdftohtml -xml output.
    Groups <text> nodes by (page, y) with tolerances, then merges lines to paragraphs.
    """
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return ""
    root = tree.getroot()

    items: List[Tuple[int, float, float, str]] = []
    for page in root.findall(".//page"):
        pnum = int(page.get("number", "1"))
        for t in page.findall(".//text"):
            left = t.get("left", "0") or "0"
            top  = t.get("top", "0") or "0"
            try:
                x = float(left); y = float(top)
            except ValueError:
                x = 0.0; y = 0.0
            txt = "".join(t.itertext()).strip()
            if txt:
                items.append((pnum, y, x, txt))

    if not items:
        return ""
    items.sort(key=lambda r: (r[0], r[1], r[2]))

    # thresholds
    line_tol = 6.0    # px change to start a new line
    para_tol = 18.0   # px change to start a new paragraph

    out_lines: List[str] = []
    paragraphs: List[str] = []

    curr_p = None
    curr_y: Optional[float] = None
    line_tokens: List[Tuple[int,float,float,str]] = []

    def flush_line():
        nonlocal line_tokens, out_lines
        if line_tokens:
            line_tokens.sort(key=lambda r: r[2])
            line = " ".join(tok[3] for tok in line_tokens if tok[3])
            if line:
                out_lines.append(line)
            line_tokens = []

    def flush_paragraph():
        nonlocal paragraphs, out_lines
        if out_lines:
            paragraphs.append(" ".join(out_lines).strip())
            out_lines = []

    for p, y, x, txt in items:
        if curr_p != p:
            flush_line()
            flush_paragraph()
            curr_p = p
            curr_y = y
        # new line?
        if curr_y is None or abs(y - curr_y) > line_tol:
            flush_line()
            if curr_y is not None and abs(y - curr_y) > para_tol:
                flush_paragraph()
            curr_y = y
        line_tokens.append((p, y, x, txt))

    flush_line()
    flush_paragraph()

    body = "\n".join(f"<p>{html.escape(par)}</p>" for par in paragraphs if par)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<meta name="generator" content="pdftohtml -xml → paragraphs"/>
<style>
  body{{margin:2rem auto;max-width:900px;line-height:1.55;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
  p{{margin:0 0 0.9rem}}
</style>
</head>
<body>
{body}
</body>
</html>"""

def pdf_page_count(pdf_path: Path) -> int:
    cp = try_run(f'pdfinfo "{pdf_path}"')
    if not cp:
        return 0
    out = cp.stdout.decode("utf-8", errors="ignore")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0

def is_low_yield(text: str, pages: int, min_chars_per_page: int = 200) -> bool:
    # Treat as low yield if extremely short compared to page count.
    if not text or pages <= 0:
        return True
    return (len(text) / max(1, pages)) < min_chars_per_page

def is_low_yield(text: str, pages: int, min_chars_per_page: int = 200) -> bool:
    # Treat as low yield if extremely short compared to page count.
    if not text or pages <= 0:
        return True
    return (len(text) / max(1, pages)) < min_chars_per_page

# ----------------------- converters -----------------------

def convert_pdf_to_html_text_first(pdf_path: Path, out_html: Path, enable_ocr: bool, text_only: bool) -> str:
    title = pdf_path.name
    pages = pdf_page_count(pdf_path)

    # 1) pdftotext (Poppler)
    for args in ('-enc UTF-8 -layout', '-enc UTF-8', '-enc UTF-8 -raw'):
        cp = try_run(f'pdftotext {args} "{pdf_path}" -')
        if cp:
            txt = cp.stdout.decode("utf-8", errors="ignore").strip()
            if txt and not is_low_yield(txt, pages):
                out_html.write_text(write_html(txt, title), encoding="utf-8")
                return f"[OK] pdftotext → {out_html.name}"
            # else: low-yield; keep trying next extractor

    # 2) mutool
    if which("mutool"):
        import tempfile, glob
        with tempfile.TemporaryDirectory() as td:
            outpat = Path(td) / "p-%06d.txt"
            cp = try_run(f'mutool draw -F txt -o "{outpat}" "{pdf_path}"')
            if cp:
                parts = sorted(glob.glob(str(Path(td) / "p-*.txt")))
                text = "\n\n".join(Path(p).read_text(encoding="utf-8", errors="ignore") for p in parts)
                if text.strip() and not is_low_yield(text, pages):
                    out_html.write_text(write_html(text, title), encoding="utf-8")
                    return f"[OK] mutool → {out_html.name}"

    # 3) pdfminer.six
    cp = try_run(f'python3 -m pdfminer.high_level "{pdf_path}"')
    if cp:
        text = cp.stdout.decode("utf-8", errors="ignore").strip()
        if text and not is_low_yield(text, pages):
            out_html.write_text(write_html(text, title), encoding="utf-8")
            return f"[OK] pdfminer → {out_html.name}"

    # 4) pdftohtml -xml → rebuild
    base = out_html.with_suffix("")
    xml_base = base.parent / (base.stem + "_xml")
    cp = try_run(f'pdftohtml -xml -q -i "{pdf_path}" "{xml_base}"')
    if cp:
        xml_path = xml_base.with_suffix(".xml")
        if xml_path.exists():
            rebuilt = xml_to_html_paragraphs(xml_path, title)
            if rebuilt.strip() and not is_low_yield(rebuilt, pages, min_chars_per_page=100):
                out_html.write_text(rebuilt, encoding="utf-8")
                try: xml_path.unlink()
                except Exception: pass
                return f"[OK] pdftohtml-xml → {out_html.name}"

    # 5) OCR (force it for watermarked/fake-text PDFs)
    if enable_ocr and which("ocrmypdf"):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ocr_pdf = Path(td) / "ocr.pdf"
            # NOTE: use --force-ocr instead of --skip-text
            proc = subprocess.Popen(
                f'ocrmypdf --force-ocr --rotate-pages --deskew --jobs {os.cpu_count() or 4} '
                f'--language eng "{pdf_path}" "{ocr_pdf}"',
                shell=True
            )  # inherits stdout/stderr → you’ll see the progress bar
            ret = proc.wait()
            if ret == 0 and ocr_pdf.exists():
                cp2 = try_run(f'pdftotext -enc UTF-8 -layout "{ocr_pdf}" -')
                if cp2:
                    txt = cp2.stdout.decode("utf-8", errors="ignore").strip()
                    if txt and not is_low_yield(txt, pages, min_chars_per_page=150):
                        out_html.write_text(write_html(txt, title), encoding="utf-8")
                        return f"[OK] ocr → {out_html.name}"

    # 6) Last resort: page images
    flags = "-s -noframes -hidden -i -q -zoom 1.3 -p"
    cp = try_run(f'pdftohtml {flags} "{pdf_path}" "{base}"')
    if cp:
        return f"[OK] page-images → {base.with_suffix('.html').name}"
    return "[FAIL] no method succeeded"


# ----------------------- CLI -----------------------

def convert_one(pdf_path: Path, out_dir: Path, enable_ocr: bool, text_only: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / f"{safe_stem(pdf_path)}.html"
    try:
        status = convert_pdf_to_html_text_first(pdf_path, out_html, enable_ocr, text_only)
        return (pdf_path, status)
    except Exception as e:
        return (pdf_path, f"[ERROR] {e.__class__.__name__}: {e}")

def main():
    ap = argparse.ArgumentParser(description="Convert textbook PDFs to HTML with robust fallbacks.")
    ap.add_argument("input_path", help="PDF file or directory of PDFs")
    ap.add_argument("--out-dir", default="./out-html", help="Output folder for .html files")
    ap.add_argument("--enable-ocr", action="store_true", help="Use OCR as fallback (requires ocrmypdf)")
    ap.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 4)//2),
                    help="Parallel workers when input_path is a directory")
    ap.add_argument("--text-only", action="store_true",
                help="Never emit page images; skip image fallback and ignore images in pdftohtml.")

    args = ap.parse_args()

    # Hard requirements
    require("pdftotext")
    require("pdftohtml")
    # Soft (optional) tools
    require("mutool", soft=True)     # mupdf-tools
    # pdfminer is run via python -m, so no binary to check — it's optional
    require("ocrmypdf", soft=True)

    # CMaps help for Poppler (silently ignore if not present)
    if not which("pdftotext"):
        print("[warn] Poppler tools missing. Install: sudo apt-get install -y poppler-utils")
    if which("apt-get"):
        # best-effort hint to install CMaps to fix empty text issues
        pass

    src = Path(args.input_path)
    out_dir = Path(args.out_dir)

    if src.is_file():
        pdfs = [src]
    else:
        pdfs = sorted([p for p in src.rglob("*.pdf") if p.is_file()])

    if not pdfs:
        print(f"No PDFs found under {src}")
        sys.exit(1)

    print(f"Found {len(pdfs)} PDF(s). Converting with {args.workers} workers...")
    results: List[Tuple[Path,str]] = []
    if len(pdfs) == 1 or args.workers <= 1:
        for p in pdfs:
            results.append(convert_one(p, out_dir, args.enable_ocr, args.text_only))
    else:
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(convert_one, p, out_dir, args.enable_ocr) for p in pdfs]
            for f in cf.as_completed(futs):
                results.append(f.result())

    ok = 0
    for pdf_path, status in results:
        tag = "OK" if status.startswith("[OK]") else "FAIL"
        ok += int(tag == "OK")
        print(f"{tag} {pdf_path.name}: {status}")

    print(f"\nDone. Success: {ok}, Failures: {len(results)-ok}, Output: {out_dir}")

if __name__ == "__main__":
    main()
