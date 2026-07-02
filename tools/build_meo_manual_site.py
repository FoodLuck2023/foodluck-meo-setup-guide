from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont


DEFAULT_SOURCE = Path(r"C:\Users\n0ria\Dropbox\007_ツール・DX\MEO\FoodLuckMEO操作説明書")
DEFAULT_OUTPUT = Path("meo_manual_site")
DEFAULT_LOGO = Path(r"C:\Users\n0ria\Dropbox\03_SNS・Web\HP\logo_foodluckmeo.png")


@dataclass
class Section:
    title: str
    anchor: str
    text_parts: list[str] = field(default_factory=list)


@dataclass
class Manual:
    title: str
    subtitle: str
    category: str
    order: int
    slug: str
    docx_path: Path
    pdf_asset: str | None = None
    preview_asset: str | None = None
    sections: list[Section] = field(default_factory=list)
    intro_text: str = ""
    plain_text: str = ""
    image_count: int = 0


def iter_block_items(parent: DocxDocument) -> Iterable[Paragraph | Table]:
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def slugify(value: str, fallback: str = "item") -> str:
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^0-9a-zA-Z\u3040-\u30ff\u3400-\u9fff-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or fallback


def file_slug(path: Path) -> str:
    stem = path.stem
    match = re.match(r"^(\d{2})_FoodLuck_MEO_(.+?)(?:_操作説明書)?$", stem)
    if match:
        return f"{match.group(1)}-{slugify(match.group(2))}"
    return slugify(stem)


def title_from_path(path: Path) -> tuple[str, str, str, int]:
    stem = path.stem
    match = re.match(r"^(\d{2})_FoodLuck_MEO_(.+?)(?:_操作説明書)?$", stem)
    if match:
        number = int(match.group(1))
        title = match.group(2).replace("_", " ")
        return title, f"FoodLuck MEO 操作説明書 {match.group(1)}", "機能別マニュアル", number
    if "FAQ" in stem:
        return stem.replace("_", " "), "FAQ・運用資料", "FAQ・運用資料", 200
    if "運用" in stem:
        return stem.replace("_", " "), "運用マニュアル", "FAQ・運用資料", 210
    return stem.replace("_", " "), "参考資料", "その他資料", 900


def rel_attr(element, name: str) -> str | None:
    return element.get(qn(name))


def paragraph_runs_html(paragraph: Paragraph, manual: Manual, media_dir: Path) -> tuple[str, list[str]]:
    parts: list[str] = []
    texts: list[str] = []
    for run in paragraph.runs:
        text = run.text
        if text:
            escaped = html.escape(text)
            if run.bold:
                escaped = f"<strong>{escaped}</strong>"
            if run.italic:
                escaped = f"<em>{escaped}</em>"
            parts.append(escaped)
            texts.append(text)

        for drawing in run._element.xpath(".//a:blip"):
            rid = rel_attr(drawing, "r:embed") or rel_attr(drawing, "r:link")
            if not rid or rid not in paragraph.part.related_parts:
                continue
            image_part = paragraph.part.related_parts[rid]
            ext = Path(image_part.partname).suffix or ".png"
            digest = hashlib.sha1(image_part.blob).hexdigest()[:10]
            image_name = f"{manual.slug}-{digest}{ext}"
            image_path = media_dir / image_name
            if not image_path.exists():
                image_path.write_bytes(image_part.blob)
            parts.append(
                f'<figure><img src="../assets/manual-images/{html.escape(image_name)}" '
                f'alt="{html.escape(manual.title)}の画面説明"></figure>'
            )
            manual.image_count += 1
    return "".join(parts), texts


def table_html(table: Table) -> tuple[str, str]:
    rows: list[str] = []
    plain_rows: list[str] = []
    for row_index, row in enumerate(table.rows):
        cells: list[str] = []
        plain_cells: list[str] = []
        tag = "th" if row_index == 0 else "td"
        for cell in row.cells:
            text = re.sub(r"\s+", " ", cell.text.strip())
            cells.append(f"<{tag}>{html.escape(text)}</{tag}>")
            plain_cells.append(text)
        rows.append("<tr>" + "".join(cells) + "</tr>")
        plain_rows.append(" ".join(plain_cells))
    return '<div class="table-wrap"><table>' + "".join(rows) + "</table></div>", "\n".join(plain_rows)


def close_list(open_list: str | None) -> tuple[str, str | None]:
    if not open_list:
        return "", None
    return f"</{open_list}>", None


def convert_docx(docx_path: Path, output_dir: Path) -> tuple[Manual, str]:
    title, subtitle, category, order = title_from_path(docx_path)
    manual = Manual(
        title=title,
        subtitle=subtitle,
        category=category,
        order=order,
        slug=file_slug(docx_path),
        docx_path=docx_path,
    )
    document = Document(str(docx_path))
    media_dir = output_dir / "assets" / "manual-images"
    html_blocks: list[str] = []
    text_buffer: list[str] = []
    open_list: str | None = None
    current_section: Section | None = None
    anchor_counts: dict[str, int] = {}

    def unique_anchor(text: str) -> str:
        base = slugify(text, "section")
        count = anchor_counts.get(base, 0) + 1
        anchor_counts[base] = count
        return base if count == 1 else f"{base}-{count}"

    for block in iter_block_items(document):
        if isinstance(block, Table):
            closer, open_list = close_list(open_list)
            if closer:
                html_blocks.append(closer)
            table_markup, table_text = table_html(block)
            html_blocks.append(table_markup)
            text_buffer.append(table_text)
            if current_section:
                current_section.text_parts.append(table_text)
            continue

        text = re.sub(r"\s+", " ", block.text.strip())
        style_name = block.style.name if block.style else ""
        markup, run_texts = paragraph_runs_html(block, manual, media_dir)
        if not text and not markup:
            continue

        if style_name.startswith("Heading 1") or style_name == "Title":
            closer, open_list = close_list(open_list)
            if closer:
                html_blocks.append(closer)
            anchor = unique_anchor(text)
            current_section = Section(title=text, anchor=anchor)
            manual.sections.append(current_section)
            html_blocks.append(f'<h2 id="{html.escape(anchor)}">{html.escape(text)}</h2>')
        elif style_name.startswith("Heading 2"):
            closer, open_list = close_list(open_list)
            if closer:
                html_blocks.append(closer)
            anchor = unique_anchor(text)
            html_blocks.append(f'<h3 id="{html.escape(anchor)}">{html.escape(text)}</h3>')
        elif "List Number" in style_name:
            if open_list != "ol":
                closer, open_list = close_list(open_list)
                if closer:
                    html_blocks.append(closer)
                html_blocks.append("<ol>")
                open_list = "ol"
            html_blocks.append(f"<li>{markup or html.escape(text)}</li>")
        elif "List Bullet" in style_name:
            if open_list != "ul":
                closer, open_list = close_list(open_list)
                if closer:
                    html_blocks.append(closer)
                html_blocks.append("<ul>")
                open_list = "ul"
            html_blocks.append(f"<li>{markup or html.escape(text)}</li>")
        else:
            closer, open_list = close_list(open_list)
            if closer:
                html_blocks.append(closer)
            class_name = "lead" if not manual.sections and len(text_buffer) < 3 else ""
            class_attr = f' class="{class_name}"' if class_name else ""
            html_blocks.append(f"<p{class_attr}>{markup or html.escape(text)}</p>")

        if text:
            text_buffer.append(text)
            if current_section:
                current_section.text_parts.append(text)

    closer, open_list = close_list(open_list)
    if closer:
        html_blocks.append(closer)

    manual.plain_text = "\n".join(text_buffer)
    manual.intro_text = " ".join(text_buffer[:4])[:160]
    if not manual.sections:
        manual.sections.append(Section(title=manual.title, anchor="top", text_parts=text_buffer))
    return manual, "\n".join(html_blocks)


def find_pdf(docx_path: Path) -> Path | None:
    exact = docx_path.with_suffix(".pdf")
    return exact if exact.exists() else None


def find_preview(docx_path: Path, all_previews: list[Path]) -> Path | None:
    stem = docx_path.stem
    candidates: list[Path] = []
    if stem.endswith("_操作説明書"):
        candidates.append(docx_path.with_name(stem.replace("_操作説明書", "_プレビュー") + ".png"))
    candidates.append(docx_path.with_name(stem + "_プレビュー.png"))
    for candidate in candidates:
        if candidate.exists():
            return candidate

    compact = re.sub(r"(FoodLuck|MEO|操作説明書|飲食店向け|_|-)", "", stem)
    for preview in all_previews:
        pcompact = re.sub(r"(FoodLuck|MEO|プレビュー|飲食店向け|_|-|[0-9])", "", preview.stem)
        if compact and (compact in pcompact or pcompact in compact):
            return preview
    return None


def make_placeholder_preview(manual: Manual, preview_dir: Path) -> str:
    name = f"{manual.slug}-preview.png"
    out_path = preview_dir / name
    if out_path.exists():
        return f"assets/previews/{name}"

    image = Image.new("RGB", (1200, 760), "#f7f9fc")
    draw = ImageDraw.Draw(image)
    try:
        font_title = ImageFont.truetype("meiryo.ttc", 54)
        font_sub = ImageFont.truetype("meiryo.ttc", 28)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    draw.rectangle((60, 60, 1140, 700), outline="#d7e0ea", width=3)
    draw.rectangle((60, 60, 1140, 150), fill="#15324b")
    draw.text((100, 90), "FoodLuck MEO", fill="white", font=font_sub)
    draw.text((100, 260), manual.title, fill="#15324b", font=font_title)
    draw.text((100, 345), manual.subtitle, fill="#5b6b7a", font=font_sub)
    image.save(out_path)
    return f"assets/previews/{name}"


def copy_asset(source: Path, dest_dir: Path, prefix: str = "") -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = prefix + source.name
    destination = dest_dir / safe_name
    shutil.copy2(source, destination)
    return f"assets/{dest_dir.name}/{safe_name}"


def page_template(manual: Manual, article_html: str, manuals: list[Manual]) -> str:
    toc = "\n".join(
        f'<a href="#{html.escape(section.anchor)}">{html.escape(section.title)}</a>'
        for section in manual.sections
    )
    nav_links = "\n".join(
        f'<a href="{html.escape(other.slug)}.html">{html.escape(other.title)}</a>'
        for other in manuals
        if other.category == manual.category and other.slug != manual.slug
    )
    pdf_link = (
        f'<a class="button secondary" href="../{html.escape(manual.pdf_asset)}" target="_blank" rel="noopener">PDFで見る</a>'
        if manual.pdf_asset
        else ""
    )
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(manual.title)} | FoodLuck MEO操作説明書</title>
  <link rel="stylesheet" href="../assets/site.css">
</head>
<body data-page="manual">
  <header class="site-header">
    <a class="brand" href="../index.html">
      <img src="../assets/brand/logo_foodluckmeo_display.png" alt="FoodLuck MEO">
      <span>操作説明書</span>
    </a>
    <a class="button" href="../index.html#search">検索へ戻る</a>
  </header>
  <main class="manual-layout">
    <aside class="toc-panel">
      <p class="eyebrow">{html.escape(manual.category)}</p>
      <h1>{html.escape(manual.title)}</h1>
      <p>{html.escape(manual.subtitle)}</p>
      <div class="button-row">{pdf_link}</div>
      <nav class="toc">{toc}</nav>
    </aside>
    <article class="manual-content" id="content">
      <div class="manual-meta">
        <span>{html.escape(manual.category)}</span>
        <span>{len(manual.sections)} セクション</span>
        <span>{manual.image_count} 画像</span>
      </div>
      {article_html}
    </article>
    <aside class="related-panel">
      <p class="eyebrow">同じカテゴリ</p>
      <nav>{nav_links}</nav>
    </aside>
  </main>
  <script src="../assets/manual.js"></script>
</body>
</html>
"""


def index_template(manuals: list[Manual], categories: list[str]) -> str:
    category_blocks: list[str] = []
    for category in categories:
        cards = []
        for manual in [m for m in manuals if m.category == category]:
            pdf = (
                f'<a class="small-link" href="{html.escape(manual.pdf_asset)}" target="_blank" rel="noopener">PDF</a>'
                if manual.pdf_asset
                else ""
            )
            preview = manual.preview_asset or "assets/previews/default-preview.png"
            cards.append(
                f"""<article class="manual-card">
  <a href="manuals/{html.escape(manual.slug)}.html">
    <img src="{html.escape(preview)}" alt="{html.escape(manual.title)}のプレビュー">
    <div>
      <p class="eyebrow">{html.escape(manual.subtitle)}</p>
      <h3>{html.escape(manual.title)}</h3>
      <p>{html.escape(manual.intro_text)}</p>
    </div>
  </a>
  <div class="card-actions">
    <a class="small-link" href="manuals/{html.escape(manual.slug)}.html">Webで読む</a>
    {pdf}
  </div>
</article>"""
            )
        category_blocks.append(
            f"""<section class="manual-section">
  <div class="section-heading">
    <p class="eyebrow">{len(cards)}件</p>
    <h2>{html.escape(category)}</h2>
  </div>
  <div class="manual-grid">
    {''.join(cards)}
  </div>
</section>"""
        )

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FoodLuck MEO操作説明書</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="home-hero">
    <div class="hero-copy">
      <img class="hero-logo" src="assets/brand/logo_foodluckmeo_display.png" alt="FoodLuck MEO">
      <h1>操作説明書</h1>
      <p>機能別マニュアル、FAQ、運用資料をまとめて検索できます。</p>
    </div>
    <div class="hero-stats">
      <span><strong>{len(manuals)}</strong>資料</span>
      <span><strong>{sum(len(m.sections) for m in manuals)}</strong>章</span>
    </div>
  </header>
  <main>
    <section class="search-panel" id="search">
      <label for="searchInput">キーワード検索</label>
      <div class="search-box">
        <input id="searchInput" type="search" placeholder="例：クチコミ、投稿、順位、GBP、写真">
        <button id="clearSearch" type="button" aria-label="検索語を消す">×</button>
      </div>
      <div id="searchMeta" class="search-meta"></div>
      <div id="searchResults" class="search-results"></div>
    </section>
    {''.join(category_blocks)}
  </main>
  <script src="assets/search-index.js"></script>
  <script src="assets/search.js"></script>
</body>
</html>
"""


SITE_CSS = """
:root {
  color-scheme: light;
  --ink: #172535;
  --muted: #647283;
  --line: #d9e2ec;
  --panel: #ffffff;
  --soft: #f5f8fb;
  --navy: #15324b;
  --accent: #b2292e;
  --accent-soft: #fff1f2;
  --shadow: 0 18px 45px rgba(20, 45, 70, 0.10);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Yu Gothic", "Meiryo", system-ui, sans-serif;
  color: var(--ink);
  background: var(--soft);
  line-height: 1.75;
}
a { color: inherit; }
.home-hero,
.site-header {
  background: var(--navy);
  color: #fff;
  padding: 32px clamp(18px, 4vw, 56px);
}
.home-hero {
  min-height: 240px;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}
.hero-copy {
  display: grid;
  gap: 14px;
  max-width: 760px;
}
.hero-logo {
  display: block;
  width: min(520px, 100%);
  height: auto;
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, .18);
}
.home-hero h1 {
  margin: 0;
  font-size: clamp(36px, 6vw, 72px);
  line-height: 1.05;
}
.home-hero p { max-width: 720px; margin: 0; color: #dce8f2; }
.hero-stats { display: flex; gap: 12px; flex-wrap: wrap; }
.hero-stats span {
  min-width: 112px;
  border: 1px solid rgba(255,255,255,.22);
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(255,255,255,.08);
}
.hero-stats strong { display: block; font-size: 28px; line-height: 1.1; }
.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 20;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  font-weight: 700;
}
.brand img {
  width: min(240px, 48vw);
  height: auto;
  background: #fff;
  border-radius: 6px;
  padding: 6px 8px;
}
.brand span { white-space: nowrap; }
main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
.search-panel {
  margin: -40px auto 34px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: clamp(18px, 3vw, 28px);
  position: relative;
}
.search-panel label {
  display: block;
  font-weight: 700;
  margin-bottom: 10px;
}
.search-box {
  display: grid;
  grid-template-columns: 1fr 44px;
  border: 2px solid var(--navy);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.search-box input {
  border: 0;
  padding: 14px 16px;
  font-size: 16px;
  outline: none;
  min-width: 0;
}
.search-box button {
  border: 0;
  border-left: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-size: 22px;
  cursor: pointer;
}
.search-meta { min-height: 28px; margin-top: 10px; color: var(--muted); }
.search-results { display: grid; gap: 10px; }
.result-card {
  display: block;
  text-decoration: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
  background: #fff;
}
.result-card:hover { border-color: var(--accent); }
.result-card strong { color: var(--accent); }
.manual-section { margin: 42px 0; }
.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.section-heading h2 { margin: 0; font-size: 28px; }
.eyebrow {
  margin: 0;
  color: var(--accent);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0;
}
.manual-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.manual-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.manual-card > a {
  display: grid;
  gap: 12px;
  text-decoration: none;
  flex: 1;
}
.manual-card img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: #eef3f7;
  border-bottom: 1px solid var(--line);
}
.manual-card div { padding: 0 14px 14px; }
.manual-card h3 { margin: 4px 0 8px; line-height: 1.35; font-size: 18px; }
.manual-card p { margin: 0; color: var(--muted); font-size: 14px; }
.card-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 1px solid var(--line);
  padding: 10px 14px;
}
.small-link {
  color: var(--navy);
  font-weight: 700;
  text-decoration: none;
}
.button,
.button.secondary {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 8px 14px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 700;
}
.button { background: #fff; color: var(--navy); }
.button.secondary {
  border: 1px solid var(--line);
  background: var(--soft);
}
.button-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
.manual-layout {
  width: min(1480px, calc(100% - 32px));
  display: grid;
  grid-template-columns: 290px minmax(0, 820px) 240px;
  gap: 22px;
  align-items: start;
  margin-top: 24px;
  margin-bottom: 60px;
}
.toc-panel,
.related-panel {
  position: sticky;
  top: 94px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
}
.toc-panel h1 { margin: 4px 0 6px; font-size: 26px; line-height: 1.25; }
.toc-panel p { color: var(--muted); }
.toc,
.related-panel nav { display: grid; gap: 6px; margin-top: 18px; }
.toc a,
.related-panel a {
  text-decoration: none;
  color: var(--ink);
  border-radius: 6px;
  padding: 7px 8px;
}
.toc a:hover,
.related-panel a:hover { background: var(--soft); color: var(--accent); }
.manual-content {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: clamp(20px, 4vw, 46px);
  min-width: 0;
}
.manual-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.manual-meta span {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--muted);
  font-size: 13px;
}
.manual-content h2 {
  margin: 44px 0 14px;
  padding-top: 10px;
  color: var(--navy);
  border-top: 3px solid var(--navy);
  font-size: 27px;
  line-height: 1.35;
}
.manual-content h2:first-of-type { margin-top: 10px; }
.manual-content h3 {
  margin: 30px 0 10px;
  color: var(--navy);
  font-size: 21px;
}
.manual-content p { margin: 0 0 16px; }
.manual-content .lead {
  background: #eef5f9;
  border-left: 4px solid var(--navy);
  padding: 12px 14px;
}
.manual-content figure {
  margin: 22px 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.manual-content img {
  display: block;
  max-width: 100%;
  height: auto;
}
.manual-content ol,
.manual-content ul { padding-left: 1.4em; margin: 0 0 16px; }
.table-wrap {
  overflow-x: auto;
  margin: 18px 0;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 620px;
  background: #fff;
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}
th { background: #eef3f7; color: var(--navy); }
mark.search-hit {
  background: #ffe28a;
  color: #1c2430;
  padding: 1px 2px;
}
@media (max-width: 1100px) {
  .manual-layout { grid-template-columns: 250px minmax(0, 1fr); }
  .related-panel { display: none; }
}
@media (max-width: 780px) {
  .home-hero { display: block; min-height: 220px; }
  .hero-stats { margin-top: 22px; }
  .site-header { position: static; gap: 14px; flex-wrap: wrap; }
  .manual-layout { display: block; width: min(100% - 24px, 760px); }
  .toc-panel { position: static; margin-bottom: 14px; }
  .manual-content { padding: 20px; }
  main { width: min(100% - 24px, 1180px); }
  .search-panel { margin-top: -24px; }
}
"""


SEARCH_JS = """
const input = document.getElementById('searchInput');
const results = document.getElementById('searchResults');
const meta = document.getElementById('searchMeta');
const clearButton = document.getElementById('clearSearch');

function normalize(value) {
  return (value || '').toLowerCase().replace(/\\s+/g, ' ').trim();
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[char]));
}

function snippet(text, terms) {
  const lower = text.toLowerCase();
  const first = terms.map(term => lower.indexOf(term)).filter(index => index >= 0).sort((a, b) => a - b)[0] || 0;
  const start = Math.max(0, first - 52);
  const raw = text.slice(start, start + 150);
  let escaped = escapeHtml((start > 0 ? '...' : '') + raw + (start + 150 < text.length ? '...' : ''));
  for (const term of terms) {
    if (!term) continue;
    escaped = escaped.replace(new RegExp(`(${term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')})`, 'ig'), '<strong>$1</strong>');
  }
  return escaped;
}

function render() {
  const query = normalize(input.value);
  const terms = query.split(' ').filter(Boolean);
  results.innerHTML = '';
  if (!terms.length) {
    meta.textContent = 'キーワードを入れると、該当する説明書と章が表示されます。';
    return;
  }
  const matches = window.SEARCH_INDEX
    .map(item => ({ item, haystack: normalize(`${item.manual} ${item.section} ${item.text}`) }))
    .filter(({ haystack }) => terms.every(term => haystack.includes(term)))
    .slice(0, 30);

  meta.textContent = `${matches.length}件見つかりました`;
  if (!matches.length) {
    results.innerHTML = '<p class="search-meta">別の言葉で検索してください。</p>';
    return;
  }
  results.innerHTML = matches.map(({ item }) => {
    const url = `${item.url}?q=${encodeURIComponent(query)}#${item.anchor}`;
    return `<a class="result-card" href="${url}">
      <span class="eyebrow">${escapeHtml(item.category)}</span>
      <h3>${escapeHtml(item.manual)} / ${escapeHtml(item.section)}</h3>
      <p>${snippet(item.text, terms)}</p>
    </a>`;
  }).join('');
}

input.addEventListener('input', render);
clearButton.addEventListener('click', () => {
  input.value = '';
  input.focus();
  render();
});
render();
"""


MANUAL_JS = """
function highlightTerm(term) {
  if (!term) return;
  const content = document.getElementById('content');
  if (!content) return;
  const pattern = new RegExp(term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'gi');
  const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !pattern.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
      pattern.lastIndex = 0;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const span = document.createElement('span');
    span.innerHTML = node.nodeValue.replace(pattern, '<mark class="search-hit">$&</mark>');
    node.parentNode.replaceChild(span, node);
  }
  const target = location.hash ? document.querySelector(location.hash) : document.querySelector('mark.search-hit');
  if (target) setTimeout(() => target.scrollIntoView({ block: 'start' }), 120);
}

const params = new URLSearchParams(location.search);
highlightTerm(params.get('q'));
"""


def write_static_assets(output_dir: Path) -> None:
    assets = output_dir / "assets"
    (assets / "manual-images").mkdir(parents=True, exist_ok=True)
    (assets / "previews").mkdir(parents=True, exist_ok=True)
    (assets / "pdfs").mkdir(parents=True, exist_ok=True)
    (assets / "brand").mkdir(parents=True, exist_ok=True)
    if DEFAULT_LOGO.exists():
        shutil.copy2(DEFAULT_LOGO, assets / "brand" / "logo_foodluckmeo.png")
        original = Image.open(DEFAULT_LOGO).convert("RGBA")
        display = Image.new("RGBA", original.size, "#ffffff")
        display.alpha_composite(original)
        display.convert("RGB").save(assets / "brand" / "logo_foodluckmeo_display.png")
    (output_dir / "manuals").mkdir(parents=True, exist_ok=True)
    (assets / "site.css").write_text(SITE_CSS.strip() + "\n", encoding="utf-8")
    (assets / "search.js").write_text(SEARCH_JS.strip() + "\n", encoding="utf-8")
    (assets / "manual.js").write_text(MANUAL_JS.strip() + "\n", encoding="utf-8")


def write_readme(output_dir: Path, source_dir: Path, manual_count: int) -> None:
    readme = f"""# FoodLuck MEO操作説明書サイト

このフォルダーは、Wordファイルを正本として自動生成した静的Webサイトです。

## 開き方

`index.html` をブラウザで開くと、トップページから各説明書へ移動できます。

## 更新方法

1. 元フォルダー内のWord説明書を修正します。
2. 下記のコマンドを、このプロジェクトフォルダーで実行します。

```powershell
C:\\Users\\n0ria\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe tools\\build_meo_manual_site.py
```

## 生成内容

- 生成元: `{source_dir}`
- 生成資料数: {manual_count}
- PDFは `assets/pdfs` にコピーされています。
- Word内画像は `assets/manual-images` に抽出されています。
- 検索データは `assets/search-index.js` に生成されています。
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def build(source_dir: Path, output_dir: Path) -> list[Manual]:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    write_static_assets(output_dir)
    for html_file in (output_dir / "manuals").glob("*.html"):
        html_file.unlink(missing_ok=True)

    all_previews = sorted(source_dir.glob("*.png"))
    docx_files = sorted(source_dir.glob("*.docx"))
    manuals: list[Manual] = []
    rendered: dict[str, str] = {}

    for docx_path in docx_files:
        manual, article_html = convert_docx(docx_path, output_dir)
        pdf = find_pdf(docx_path)
        if pdf:
            manual.pdf_asset = copy_asset(pdf, output_dir / "assets" / "pdfs")
        preview = find_preview(docx_path, all_previews)
        if preview:
            manual.preview_asset = copy_asset(preview, output_dir / "assets" / "previews")
        else:
            manual.preview_asset = make_placeholder_preview(manual, output_dir / "assets" / "previews")
        manuals.append(manual)
        rendered[manual.slug] = article_html

    manuals.sort(key=lambda item: (item.category != "機能別マニュアル", item.category, item.order, item.title))
    categories = []
    for manual in manuals:
        if manual.category not in categories:
            categories.append(manual.category)

    for manual in manuals:
        page = page_template(manual, rendered[manual.slug], manuals)
        (output_dir / "manuals" / f"{manual.slug}.html").write_text(page, encoding="utf-8")

    search_index = []
    for manual in manuals:
        for section in manual.sections:
            text = re.sub(r"\s+", " ", " ".join(section.text_parts)).strip()
            if not text:
                text = manual.plain_text[:500]
            search_index.append(
                {
                    "manual": manual.title,
                    "category": manual.category,
                    "section": section.title,
                    "anchor": section.anchor,
                    "url": f"manuals/{manual.slug}.html",
                    "text": text[:3000],
                }
            )
    (output_dir / "assets" / "search-index.js").write_text(
        "window.SEARCH_INDEX = " + json.dumps(search_index, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(index_template(manuals, categories), encoding="utf-8")
    write_readme(output_dir, source_dir, len(manuals))
    return manuals


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the FoodLuck MEO static manual site.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manuals = build(args.source, args.output)
    print(f"Built {len(manuals)} manuals into {args.output.resolve()}")


if __name__ == "__main__":
    main()
