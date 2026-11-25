from __future__ import annotations

import textwrap
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "outputs" / "notebooklm-slide-02-upload-kit"
OUT = ROOT / "outputs" / "notebooklm-slide-02-upload-kit-pdf"


def ensure_font() -> str:
    font_name = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def draw_wrapped_text(c: canvas.Canvas, text: str, x: float, y: float, width_chars: int, line_height: float, font: str, size: int) -> float:
    c.setFont(font, size)
    for paragraph in text.splitlines():
        if not paragraph.strip():
            y -= line_height
            continue
        wrapped = textwrap.wrap(paragraph, width=width_chars, break_long_words=False, replace_whitespace=False) or [paragraph]
        for line in wrapped:
            c.drawString(x, y, line)
            y -= line_height
    return y


def page_title(c: canvas.Canvas, title: str, subtitle: str, font: str) -> float:
    width, height = A4
    c.setFont(font, 22)
    c.drawString(20 * mm, height - 22 * mm, title)
    c.setFont(font, 11)
    c.drawString(20 * mm, height - 30 * mm, subtitle)
    c.line(20 * mm, height - 33 * mm, width - 20 * mm, height - 33 * mm)
    return height - 42 * mm


def build_master_pdf(font: str) -> Path:
    out_path = OUT / "slide-02-master-upload.pdf"
    c = canvas.Canvas(str(out_path), pagesize=A4)

    y = page_title(
        c,
        "約書亞記 Slide 02 NotebookLM 上傳總包",
        "主題：全迦南分地總覽圖｜十二支派的產業藍圖",
        font,
    )
    intro = """目標：
產出一張 16:9 的高品質聖經地圖投影片主視覺。
最終畫面必須由 NotebookLM 完整重製，不能只是把 FHL 地圖直接貼上。

建議上傳順序：
1. 這份 PDF
2. 四份地點 PDF

建議在 NotebookLM 貼上的生成指令：
請根據這些資料，製作一張 16:9 的 atlas 風格聖經地圖主視覺。
請清楚呈現約旦河、死海、加利利海，以及東岸與西岸各支派分布。
請明確標示四個重點地點：示羅、耶路撒冷、希伯崙、示劍。
配色方向：
- 東岸支派：柔和琥珀色
- 猶大：深金色
- 以法蓮與瑪拿西西半：橄欖綠
- 北方支派：柔和青綠
整體風格請接近 Sacred Inheritance Atlas：莊重、乾淨、高可讀性、帶神聖感與歷史地圖質感。
標籤以繁體中文為主，必要時可輔以英文小字。
"""
    draw_wrapped_text(c, intro, 20 * mm, y, 44, 6.5 * mm, font, 11)
    c.showPage()

    brief_text = (SRC / "01-slide-brief.txt").read_text(encoding="utf-8")
    y = page_title(c, "Slide 02 總說明", "來源：01-slide-brief.txt", font)
    draw_wrapped_text(c, brief_text, 20 * mm, y, 48, 6.2 * mm, font, 11)
    c.showPage()

    place_pages = [
        ("示羅", "02-shiloh-prompt.txt", "01-shiloh-map.gif"),
        ("耶路撒冷", "03-jerusalem-prompt.txt", "02-jerusalem-map.gif"),
        ("希伯崙", "04-hebron-prompt.txt", "03-hebron-map.gif"),
        ("示劍", "05-shechem-prompt.txt", "04-shechem-map.gif"),
    ]

    for cname, prompt_file, map_file in place_pages:
        y = page_title(c, f"{cname} 參考頁", f"{prompt_file} + {map_file}", font)
        prompt_text = (SRC / "prompts" / prompt_file).read_text(encoding="utf-8")
        y = draw_wrapped_text(c, prompt_text, 20 * mm, y, 44, 6.0 * mm, font, 10)

        image_path = SRC / "maps" / map_file
        img = ImageReader(str(image_path))
        img_width = 140 * mm
        img_height = 95 * mm
        c.drawImage(img, 35 * mm, 18 * mm, width=img_width, height=img_height, preserveAspectRatio=True, mask="auto")
        c.showPage()

    c.save()
    return out_path


def build_place_pdf(font: str, cname: str, prompt_file: str, map_file: str, output_name: str) -> Path:
    out_path = OUT / output_name
    c = canvas.Canvas(str(out_path), pagesize=landscape(A4))
    width, height = landscape(A4)
    c.setFont(font, 20)
    c.drawString(18 * mm, height - 18 * mm, f"{cname} NotebookLM 參考包")
    c.setFont(font, 10)
    c.drawString(18 * mm, height - 26 * mm, "請將此 PDF 上傳到 NotebookLM，作為地理與視覺參考。")
    c.line(18 * mm, height - 29 * mm, width - 18 * mm, height - 29 * mm)

    prompt_text = (SRC / "prompts" / prompt_file).read_text(encoding="utf-8")
    draw_wrapped_text(c, prompt_text, 18 * mm, height - 40 * mm, 45, 5.5 * mm, font, 10)
    image_path = SRC / "maps" / map_file
    img = ImageReader(str(image_path))
    c.drawImage(img, 155 * mm, 28 * mm, width=110 * mm, height=150 * mm, preserveAspectRatio=True, mask="auto")
    c.save()
    return out_path


def write_readme() -> Path:
    text = """# Slide 02 PDF Upload Kit

推薦上傳順序：
1. slide-02-master-upload.pdf
2. slide-02-shiloh-reference.pdf
3. slide-02-jerusalem-reference.pdf
4. slide-02-hebron-reference.pdf
5. slide-02-shechem-reference.pdf

建議 NotebookLM 任務：
- 產出一張 16:9 聖經地圖總覽主視覺
- 風格接近 Sacred Inheritance Atlas
- 不直接拼貼原始地圖，而是完整重製 atlas 視覺
- 以繁體中文標示主要地點與支派

最終請下載一張成品圖，回存為：
outputs/notebooklm-deck-package-1-3/slide-02/final-notebooklm-image.png
"""
    out_path = OUT / "README.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    font = ensure_font()
    build_master_pdf(font)
    build_place_pdf(font, "示羅", "02-shiloh-prompt.txt", "01-shiloh-map.gif", "slide-02-shiloh-reference.pdf")
    build_place_pdf(font, "耶路撒冷", "03-jerusalem-prompt.txt", "02-jerusalem-map.gif", "slide-02-jerusalem-reference.pdf")
    build_place_pdf(font, "希伯崙", "04-hebron-prompt.txt", "03-hebron-map.gif", "slide-02-hebron-reference.pdf")
    build_place_pdf(font, "示劍", "05-shechem-prompt.txt", "04-shechem-map.gif", "slide-02-shechem-reference.pdf")
    write_readme()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

