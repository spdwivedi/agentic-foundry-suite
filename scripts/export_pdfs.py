"""Markdown to PDF export engine with client-side Mermaid, KaTeX, and GDrive staging."""

import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List
import markdown


REPO_ROOT = Path(__file__).resolve().parent.parent

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false}
    ]});"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: 'neutral',
    pie: {
      useMaxWidth: true,
      textPosition: 0.75
    },
    sequence: {
      useMaxWidth: true,
      actorFontSize: 13,
      noteFontSize: 12,
      messageFontSize: 12
    },
    flowchart: {
      useMaxWidth: true,
      nodeSpacing: 30,
      rankSpacing: 35
    }
  });
</script>
<style>
  @page {
    size: A4;
    margin: 16mm 14mm 16mm 14mm;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    color: #24292f;
    margin: 24px 32px;
  }
  h1, h2, h3, h4, h5, h6 {
    color: #1f2328;
    font-weight: 600;
    page-break-after: avoid;
    break-after: avoid;
  }
  h1 { font-size: 19px; margin-top: 14px; margin-bottom: 6px; border-bottom: 2px solid #d0d7de; padding-bottom: 6px; }
  h2 { font-size: 15px; margin-top: 14px; margin-bottom: 6px; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; }
  h3 { font-size: 13px; margin-top: 10px; margin-bottom: 4px; }
  h4 { font-size: 12px; margin-top: 8px; margin-bottom: 4px; }
  p, ul, ol { margin-top: 4px; margin-bottom: 6px; }
  p, li {
    font-size: 13px;
    line-height: 1.5;
  }
  p {
    orphans: 3;
    widows: 3;
  }
  table {
    width: 100% !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
    font-size: 11px !important;
    margin: 14px 0 !important;
  }
  th, td {
    padding: 7px 9px !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    border: 1px solid #d0d7de !important;
    text-align: left;
  }
  th {
    background-color: #f6f8fa !important;
    font-weight: 600;
  }
  tr:nth-child(2n) {
    background-color: #fcfcfc !important;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
    font-size: 12px;
    padding: 0.2em 0.4em;
    margin: 0;
    background-color: rgba(175, 184, 193, 0.2);
    border-radius: 4px;
    color: #24292f;
  }
  pre {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 10px;
    overflow-x: auto;
    font-size: 11.5px;
    line-height: 1.4;
    color: #24292f;
    page-break-inside: avoid;
    break-inside: avoid;
  }
  pre code {
    background: transparent;
    padding: 0;
    font-size: 100%;
    color: #24292f;
  }
  blockquote {
    margin: 14px 0;
    padding: 0 1em;
    color: #57606a;
    border-left: 0.25em solid #0969da;
    background-color: #f8fafc;
    page-break-inside: avoid;
    break-inside: avoid;
  }
  .mermaid {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    margin: 20px auto !important;
    padding: 12px 0 !important;
    page-break-inside: avoid !important;
    break-inside: avoid !important;
    overflow: visible !important;
  }
  .mermaid svg {
    width: auto !important;
    height: auto !important;
    max-width: 580px !important;
    max-height: 300px !important;
    filter: contrast(1.08);
  }
  /* Pie chart title positioning and styling */
  .mermaid svg text.pieTitleText {
    font-size: 14px !important;
    font-weight: 600 !important;
    transform: translateY(18px) !important;
    fill: #24292f !important;
  }
  /* Give sequence and pie charts sufficient breathing room */
  .mermaid svg[id^="mermaid-"] {
    padding-top: 14px !important;
    padding-bottom: 8px !important;
  }
  hr {
    height: 1px;
    background-color: #d0d7de;
    border: none;
    margin: 20px 0;
  }
  @media print {
    body { padding: 0; margin: 0; font-size: 13px; }
    h1, h2, h3, h4 {
      break-after: avoid-page !important;
      page-break-after: avoid !important;
    }
    .mermaid, pre, table, blockquote {
      break-inside: avoid !important;
      page-break-inside: avoid !important;
    }
    p {
      orphans: 3;
      widows: 3;
    }
  }
</style>
</head>
<body>
__BODY_CONTENT__
</body>
</html>
"""


def find_edge_executable() -> str:
    """Locate Microsoft Edge executable on Windows."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Microsoft Edge executable not found.")


def preprocess_markdown(text: str) -> tuple[str, List[str]]:
    """Detect and transform all ```mermaid ... ``` blocks into <div class="mermaid"> containers,
    and protect KaTeX math blocks from Python-Markdown mangling."""
    # Convert any escaped math delimiters \$\$ to $$
    text = text.replace(r"\$\$", "$$")

    math_blocks: List[str] = []

    def _save_math(match: re.Match) -> str:
        idx = len(math_blocks)
        math_blocks.append(match.group(0))
        return f"KATEXMATHPLACEHOLDER{idx}END"

    # Display math ($$ ... $$)
    text = re.sub(r"\$\$.*?\$\$", _save_math, text, flags=re.DOTALL)
    # Inline math ($ ... $)
    text = re.sub(r"(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)", _save_math, text)

    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

    def _replace_mermaid(match: re.Match) -> str:
        diagram_code = match.group(1).strip()
        return f'\n\n<div class="mermaid">\n{diagram_code}\n</div>\n\n'

    text = pattern.sub(_replace_mermaid, text)
    return text, math_blocks


def restore_math(html: str, math_blocks: List[str]) -> str:
    """Restore exact math blocks back into the generated HTML."""
    for idx, block in enumerate(math_blocks):
        html = html.replace(f"KATEXMATHPLACEHOLDER{idx}END", block)
    return html


def render_markdown_to_pdf(source_md: Path, target_pdf: Path, edge_bin: str) -> None:
    """Convert Markdown file to PDF using python-markdown, KaTeX, Mermaid runtime, and headless Edge."""
    raw_text = source_md.read_text(encoding="utf-8")
    processed_text, math_blocks = preprocess_markdown(raw_text)

    body_html = markdown.markdown(
        processed_text,
        extensions=["extra", "tables", "fenced_code", "toc"],
    )
    body_html = restore_math(body_html, math_blocks)
    full_html = HTML_TEMPLATE.replace("__BODY_CONTENT__", body_html)

    target_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as temp_f:
        temp_f.write(full_html)
        temp_html_path = Path(temp_f.name).resolve()

    try:
        cmd = [
            edge_bin,
            "--headless",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--force-device-scale-factor=1.1",
            "--virtual-time-budget=6000",
            f"--print-to-pdf={target_pdf.resolve()}",
            f"file:///{temp_html_path.as_posix()}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if proc.returncode != 0 or not target_pdf.exists() or target_pdf.stat().st_size == 0:
            raise RuntimeError(f"Edge PDF generation failed for {source_md}: {proc.stderr}")
    finally:
        if temp_html_path.exists():
            temp_html_path.unlink()


def assemble_gdrive_staging() -> None:
    """Assemble complete Google Drive staging bundle."""
    gdrive_root = REPO_ROOT / "gdrive_upload"
    notes_pdf_dir = gdrive_root / "PDFs" / "Notes"
    reports_pdf_dir = gdrive_root / "PDFs" / "Reports"
    transcripts_root = gdrive_root / "Transcripts"

    notes_pdf_dir.mkdir(parents=True, exist_ok=True)
    reports_pdf_dir.mkdir(parents=True, exist_ok=True)

    edge_bin = find_edge_executable()

    # Convert notes/*.md
    notes_dir = REPO_ROOT / "notes"
    for md_path in sorted(notes_dir.glob("*.md")):
        pdf_path = notes_pdf_dir / f"{md_path.stem}.pdf"
        print(f"Exporting PDF: notes/{md_path.name} -> {pdf_path.relative_to(REPO_ROOT)}")
        render_markdown_to_pdf(md_path, pdf_path, edge_bin)

    # Convert reports/*.md
    reports_dir = REPO_ROOT / "reports"
    for md_path in sorted(reports_dir.glob("*.md")):
        pdf_path = reports_pdf_dir / f"{md_path.stem}.pdf"
        print(f"Exporting PDF: reports/{md_path.name} -> {pdf_path.relative_to(REPO_ROOT)}")
        render_markdown_to_pdf(md_path, pdf_path, edge_bin)

    # Copy transcripts
    for assn_dir in ["assignment-1", "assignment-2", "assignment-3"]:
        src_t_dir = REPO_ROOT / assn_dir / "transcripts"
        dst_t_dir = transcripts_root / assn_dir
        dst_t_dir.mkdir(parents=True, exist_ok=True)
        for t_file in sorted(src_t_dir.glob("*.txt")):
            dest_t_file = dst_t_dir / t_file.name
            shutil.copy2(t_file, dest_t_file)
            print(f"Copied transcript: {t_file.relative_to(REPO_ROOT)} -> {dest_t_file.relative_to(REPO_ROOT)}")

    # Copy Junior_AI_Engineer.pdf if present
    candidate_pdfs = [
        REPO_ROOT / "Junior_AI_Engineer.pdf",
        Path.home() / "Downloads" / "Junior_AI_Engineer.pdf",
    ]
    for c_pdf in candidate_pdfs:
        if c_pdf.exists():
            target_file = gdrive_root / "Junior_AI_Engineer.pdf"
            shutil.copy2(c_pdf, target_file)
            print(f"Copied Junior_AI_Engineer.pdf from {c_pdf} -> {target_file.relative_to(REPO_ROOT)}")
            break


def main():
    """CLI entrypoint for upgraded PDF export and bundle staging."""
    start_time = time.time()
    print("=" * 80)
    print("STARTING MERMAID & KATEX-ENABLED PDF EXPORT & GDRIVE STAGING")
    print("=" * 80)
    assemble_gdrive_staging()
    elapsed = round(time.time() - start_time, 2)
    print(f"\n[SUCCESS] Export and staging completed in {elapsed}s.")
    print(f"Staging Location: {REPO_ROOT / 'gdrive_upload'}\n")


if __name__ == "__main__":
    main()
