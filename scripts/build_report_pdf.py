#!/usr/bin/env python3
"""Converte report/report.md para report/report.pdf usando markdown + Chrome headless."""

import shutil
import subprocess
import sys
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = ROOT / "report" / "report.md"
REPORT_HTML = ROOT / "report" / "report.html"
REPORT_PDF = ROOT / "report" / "report.pdf"

CSS = """
<style>
  @page {
    size: A4;
    margin: 20mm 18mm;
  }
  body {
    font-family: 'DejaVu Sans', 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #222;
    max-width: 180mm;
    margin: 0 auto;
  }
  h1, h2, h3, h4 {
    color: #1a1a1a;
    margin-top: 1.2em;
  }
  h1 { font-size: 22pt; border-bottom: 2px solid #333; padding-bottom: 6px; }
  h2 { font-size: 16pt; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  h3 { font-size: 13pt; }
  h4 { font-size: 11pt; }
  code {
    font-family: 'DejaVu Sans Mono', 'Consolas', monospace;
    background: #f1f1f1;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10pt;
  }
  pre {
    background: #f6f8fa;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 10px;
    font-size: 9.5pt;
    overflow-x: auto;
    page-break-inside: avoid;
  }
  pre code { background: transparent; padding: 0; }
  table {
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid #ccc;
    padding: 6px 10px;
    text-align: left;
  }
  th { background: #f0f0f0; }
  img {
    max-width: 100%;
    display: block;
    margin: 12px auto;
    page-break-inside: avoid;
  }
  blockquote {
    border-left: 4px solid #ccc;
    color: #555;
    margin: 10px 0;
    padding: 4px 12px;
    background: #fafafa;
  }
  strong { color: #111; }
  a { color: #0366d6; text-decoration: none; }
</style>
"""


def ensure_browser():
    candidates = ("google-chrome", "chromium", "chrome", "chromium-browser")
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    raise SystemExit("nenhum navegador headless encontrado (google-chrome / chromium)")


def rewrite_image_paths(html: str) -> str:
    # Markdown usa caminhos relativos a report/, aponta para ../results/...
    # Como o HTML e salvo em report/, os caminhos continuam corretos
    return html


def build_html(markdown_text: str) -> str:
    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
        output_format="html5",
    )
    body = rewrite_image_paths(body)
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Relatorio: Gradiente Conjugado Distribuido com Block ELLPACK</title>
{CSS}
</head>
<body>
{body}
</body>
</html>
"""


def main() -> int:
    if not REPORT_MD.exists():
        print(f"arquivo nao encontrado: {REPORT_MD}", file=sys.stderr)
        return 1
    markdown_text = REPORT_MD.read_text(encoding="utf-8")
    html = build_html(markdown_text)
    REPORT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML gerado: {REPORT_HTML}")

    browser = ensure_browser()
    uri = REPORT_HTML.resolve().as_uri()
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={REPORT_PDF}",
        "--no-pdf-header-footer",
        uri,
    ]
    print("executando:", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    if not REPORT_PDF.exists() or REPORT_PDF.stat().st_size == 0:
        print("PDF nao foi gerado pelo navegador", file=sys.stderr)
        return 2
    print(f"PDF gerado: {REPORT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
