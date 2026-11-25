import urllib.request
import re
import os
import time
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}

MODULES = [
    ('CT', '📖 壹、經文詳解與註解'),
    ('GT', '🌾 貳、讀經拾穗'),
    ('IT', '💡 叁、例證故事'),
    ('MT', '🕊️ 肆、靈修信息'),
    ('OT', '📑 伍、講章綱目'),
]

BASE_URL = "https://www.ccbiblestudy.org/"
ROOT_DIR = r"d:\Bible"
CATALOG_PATH = os.path.join(ROOT_DIR, "索引資料", "bible_books_catalog.json")

def decode_html_bytes(raw_bytes):
    meta_head = raw_bytes[:3000].decode('ascii', errors='ignore').lower()
    candidates = []
    if 'charset=utf-8' in meta_head or 'charset="utf-8"' in meta_head:
        candidates = ['utf-8', 'big5hkscs', 'cp950', 'gb18030']
    elif 'charset=big5' in meta_head or 'charset="big5"' in meta_head:
        candidates = ['big5hkscs', 'cp950', 'big5', 'utf-8', 'gb18030']
    elif 'charset=gb2312' in meta_head or 'charset=gbk' in meta_head:
        candidates = ['gb18030', 'big5hkscs', 'utf-8']
    else:
        candidates = ['utf-8', 'big5hkscs', 'cp950', 'gb18030', 'big5']
        
    for enc in candidates:
        try:
            text = raw_bytes.decode(enc)
            if any(k in text for k in ['耶穌', '基督', '約翰', '教會', '神', '使徒', '天使', '生命', '章', '註解', '拾穗', '綱目', '起初', '創世記', '耶和華', '以色列', '摩西', '大衛', '保羅']):
                return text, enc
        except Exception:
            continue
            
    for enc in ['big5hkscs', 'utf-8', 'cp950']:
        try:
            return raw_bytes.decode(enc, errors='replace'), f"{enc}(replace)"
        except:
            pass
    return raw_bytes.decode('utf-8', errors='ignore'), 'utf-8(ignore)'

def clean_paragraph_text(p_tag):
    text = p_tag.get_text(separator=' ', strip=True)
    text = text.replace('\xa0', ' ').replace('\u3000', ' ')
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'【\s*([^】]+?)\s*】', r'【\1】', text)
    text = re.sub(r'〔\s*([^〕]+?)\s*〕', r'〔\1〕', text)
    text = re.sub(r'\(\s*([^)]+?)\s*\)', r'(\1)', text)
    text = re.sub(r'（\s*([^）]+?)\s*）', r'（\1）', text)
    text = re.sub(r'「\s*([^」]+?)\s*」', r'「\1」', text)
    text = re.sub(r'『\s*([^』]+?)\s*』', r'『\1』', text)
    text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
    return text

def parse_html_to_markdown(html_content, book_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup.find_all(['script', 'style', 'head']):
        tag.decompose()
        
    tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'])
    md_lines = []
    
    for tag in tags:
        if tag.name not in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'] and tag.find(['p', 'h1', 'h2', 'h3']):
            continue
            
        text = clean_paragraph_text(tag)
        if not text or ('返回首頁' in text and '返回' in text):
            continue
            
        if re.match(r'^【.*?\d+.*?】', text):
            md_lines.append(f"\n### {text}\n")
        elif re.match(r'^【[^】]+】$', text):
            md_lines.append(f"\n#### {text}\n")
        elif re.match(r'^[壹貳參肆伍陸柒捌玖拾]、', text):
            md_lines.append(f"\n### {text}\n")
        elif re.match(r'^[一二三四五六七八九十]+、', text):
            md_lines.append(f"\n##### {text}\n")
        elif text.startswith('〔') and '〕' in text:
            closing_idx = text.find('〕')
            tag_name = text[:closing_idx+1]
            content = text[closing_idx+1:].strip()
            md_lines.append(f"> **{tag_name}** {content}\n")
        elif text.startswith('──') or text.startswith('——'):
            md_lines.append(f"\n*{text}*\n")
        else:
            md_lines.append(f"{text}\n\n")
            
    return "".join(md_lines)

def fetch_and_decode_url(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as res:
                raw_bytes = res.read()
                html_text, used_enc = decode_html_bytes(raw_bytes)
                return html_text
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(0.4)
    return None

def fetch_and_convert_pdf_to_md(pdf_url, md_path, title):
    """
    Downloads PDF to temporary storage, extracts clean text to Markdown, and deletes PDF.
    """
    tmp_pdf = None
    try:
        req = urllib.request.Request(pdf_url, headers=headers)
        with urllib.request.urlopen(req, timeout=40) as res:
            pdf_bytes = res.read()
            
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
            tf.write(pdf_bytes)
            tmp_pdf = tf.name
            
        doc = fitz.open(tmp_pdf)
        md_lines = [f"# {title}\n\n", "> 格式：Markdown 數位文字重構版\n\n---\n\n"]
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")
            if not text.strip():
                continue
            raw_lines = text.splitlines()
            for line in raw_lines:
                l = line.strip()
                if not l or re.match(r'^\d+$', l) or re.match(r'^第\s*\d+\s*頁$', l):
                    continue
                if re.match(r'^[壹貳參肆伍陸柒捌玖拾]、', l):
                    md_lines.append(f"\n## {l}\n")
                elif re.match(r'^[一二三四五六七八九十]+、', l):
                    md_lines.append(f"\n### {l}\n")
                elif l.startswith('【') and '】' in l:
                    md_lines.append(f"\n### {l}\n")
                elif l.startswith('第') and ('章' in l or '篇' in l) and len(l) < 20:
                    md_lines.append(f"\n## {l}\n")
                elif l.startswith('〔') and '〕' in l:
                    closing = l.find('〕')
                    tag = l[:closing+1]
                    content = l[closing+1:].strip()
                    md_lines.append(f"> **{tag}** {content}\n")
                else:
                    md_lines.append(f"{l}\n\n")
                    
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("".join(md_lines))
        return True, len(pdf_bytes), os.path.getsize(md_path)
    except Exception as e:
        print(f"    [-] Error processing PDF {pdf_url}: {e}")
        return False, 0, 0
    finally:
        if tmp_pdf and os.path.exists(tmp_pdf):
            try:
                os.remove(tmp_pdf)
            except Exception:
                pass

def process_single_chapter(ch, book_no, book_name, base_dir, total_chapters, book_dir):
    ch_str = f"{ch:02d}"
    if ch == 0:
        ch_title = f"{book_name} 導論與提要"
        filename = f"{book_name}_第00章_導論與提要.md"
    elif ch == total_chapters + 1:
        ch_title = f"{book_name} 全書綜合靈訓"
        filename = f"{book_name}_第{ch_str}章_綜合靈訓.md"
    else:
        ch_title = f"{book_name} 第 {ch} 章"
        filename = f"{book_name}_第{ch_str}章.md"
        
    file_path = os.path.join(book_dir, filename)
    
    # Navigation bar
    nav_links = [f"[目錄]({book_name}_目錄.md)"]
    if ch > 0:
        prev_str = f"{ch-1:02d}"
        prev_file = f"{book_name}_第00章_導論與提要.md" if ch - 1 == 0 else f"{book_name}_第{prev_str}章.md"
        nav_links.append(f"[上一章 ({ch-1})]({prev_file})")
    if ch < total_chapters + 1:
        next_str = f"{ch+1:02d}"
        next_file = f"{book_name}_第{next_str}章_綜合靈訓.md" if ch + 1 == total_chapters + 1 else f"{book_name}_第{next_str}章.md"
        nav_links.append(f"[下一章 ({ch+1})]({next_file})")
    nav_bar = " | ".join(nav_links)
    
    doc = [
        f"# {ch_title}\n\n",
        f"{nav_bar}\n\n",
        f"> **資料來源**：[華人基督徒查經資料網站 (ccbiblestudy.org)](https://www.ccbiblestudy.org/)\n",
        f"> **內容整合**：經文註解、讀經拾穗、例證故事、靈修信息、講章綱目\n\n",
        "---\n\n"
    ]
    
    has_content = False
    for code, mod_title in MODULES:
        unit_url = f"{BASE_URL}{base_dir}{book_no}{code}{ch_str}.htm"
        html = fetch_and_decode_url(unit_url)
        if html:
            section_md = parse_html_to_markdown(html, book_name)
            if section_md.strip():
                has_content = True
                doc.append(f"## {mod_title}\n\n")
                doc.append(section_md)
                doc.append("\n\n---\n\n")
                
    doc.append(f"\n\n{nav_bar}\n")
    
    if has_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("".join(doc))
        f_size_kb = os.path.getsize(file_path) / 1024
        return ch, ch_title, filename, f"{f_size_kb:.1f} KB"
    return None

def process_book(book_info):
    book_no = book_info['no']
    book_name = book_info['name']
    base_dir = book_info['base_dir']
    testament = book_info['testament']
    
    folder_name = f"{book_no}_{book_name}"
    book_dir = os.path.join(ROOT_DIR, folder_name)
    md_ebook_dir = os.path.join(book_dir, "電子書_MD")
    
    os.makedirs(book_dir, exist_ok=True)
    os.makedirs(md_ebook_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"📖 開始提取：[{book_no}] {testament} - {book_name}")
    print(f"📁 目的目錄：{book_dir}")
    print(f"{'='*60}")
    
    # 1. Fetch book index HTML & extract BOOK_CONFIG
    index_url = BASE_URL + book_info['href']
    index_html = fetch_and_decode_url(index_url)
    
    total_chapters = 50
    books_meta = []
    
    if index_html:
        m_chap = re.search(r'"chapters":\s*(\d+)', index_html)
        if m_chap:
            total_chapters = int(m_chap.group(1))
            
        m_books = re.search(r'"books":\s*(\[[\s\S]*?\])\s*};', index_html)
        if m_books:
            b_str = re.sub(r'//.*', '', m_books.group(1))
            b_str = re.sub(r',\s*\]', ']', b_str)
            try:
                books_meta = json.loads(b_str)
            except Exception:
                pass

    print(f"[*] 全書章數：{total_chapters} 章 | 發現電子書：{len(books_meta)} 本")
    
    # 2. Process Chapters concurrently
    chapter_summary = []
    print(f"[*] 正在抓取並轉換章節 (00～{total_chapters+1:02d})...")
    
    for ch in range(0, total_chapters + 2):
        res = process_single_chapter(ch, book_no, book_name, base_dir, total_chapters, book_dir)
        if res:
            chapter_summary.append(res)
            print(f"    [+] {res[2]} ({res[3]})")
        time.sleep(0.05)
            
    chapter_summary.sort(key=lambda x: x[0])
    
    # 3. Process PDF to MD directly (No PDF kept!)
    ebook_summary = []
    if books_meta:
        print(f"\n[*] 正在下載並轉成 Markdown (不保留 PDF，共 {len(books_meta)} 本)...")
        for b in books_meta:
            href = b.get('href')
            status = b.get('status')
            if not href or status == 'not-ready':
                continue
            no = b.get('no', '')
            title = b.get('title', '')
            author = b.get('author', '')
            
            author_str = f"_{author}" if author else ""
            idx_str = re.sub(r'^\d+BT', '', no)
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
            md_name = f"{idx_str}_{safe_title}{author_str}.md"
            md_path = os.path.join(md_ebook_dir, md_name)
            
            pdf_url = f"{BASE_URL}{base_dir}{href}"
            
            # Convert PDF -> MD directly
            ok, pdf_bytes, md_bytes = fetch_and_convert_pdf_to_md(pdf_url, md_path, f"{title} - {author}")
            if ok:
                pdf_mb = pdf_bytes / (1024*1024)
                md_kb = md_bytes / 1024
                print(f"    [+] 電子書 MD：{title} ({author}) [原PDF {pdf_mb:.2f}MB -> 轉MD {md_kb:.1f}KB]")
                ebook_summary.append((no, title, author, md_name, f"{md_kb:.1f} KB", f"{pdf_mb:.2f} MB"))
            time.sleep(0.1)

    # 4. Generate Master Index for this Book
    master_index_path = os.path.join(book_dir, f"{book_name}_目錄.md")
    idx_lines = [
        f"# 📖 {book_name} 查經與註解全書目錄\n\n",
        f"> **經卷歸類**：{testament} 第 {book_no} 卷\n",
        f"> **內容整合**：黃迦勒註解、歷代屬靈名家拾穗、例證故事、靈修信息與講章綱目\n\n",
        "## 📑 章節清單\n\n",
        "| 章節 | 說明 | Markdown 連結 | 檔案大小 |\n",
        "| :--- | :--- | :--- | :--- |\n"
    ]
    for ch, ch_title, fname, sz in chapter_summary:
        idx_lines.append(f"| **第 {ch:02d} 章** | {ch_title} | [{fname}]({fname}) | {sz} |\n")
        
    if ebook_summary:
        idx_lines.append("\n---\n\n## 📚 相關名家電子書專題 (Markdown 輕量版)\n\n")
        idx_lines.append("| 編號 | 書名 | 作者 | Markdown 閱讀連結 | 檔案大小 (節省空間) |\n")
        idx_lines.append("| :--- | :--- | :--- | :--- | :--- |\n")
        for no, title, author, md_f, md_sz, pdf_sz in ebook_summary:
            idx_lines.append(f"| `{no}` | **{title}** | {author} | [{md_f}](電子書_MD/{md_f}) | **{md_sz}** *(原 PDF {pdf_sz})* |\n")
            
    with open(master_index_path, 'w', encoding='utf-8') as f:
        f.write("".join(idx_lines))
        
    print(f"\n[✓] 《{book_name}》全部處理完成！目錄：{book_name}_目錄.md")

def update_global_bible_index(catalog):
    global_idx_path = os.path.join(ROOT_DIR, "全本聖經_總目錄.md")
    lines = [
        "# 📖 華人基督徒查經資料庫 - 全本聖經 66 卷總目錄\n\n",
        "> 本資料庫完整收錄 66 卷聖經經文註解、讀經拾穗、例證故事、靈修信息、講章綱目與名家電子書（Markdown 格式）。\n\n",
        "## 📜 舊約聖經 (39 卷)\n\n",
        "| 編號 | 經卷名稱 | 經卷目錄連結 | 狀態 |\n",
        "| :--- | :--- | :--- | :--- |\n"
    ]
    
    for b in catalog:
        no = b['no']
        name = b['name']
        testament = b['testament']
        folder = f"{no}_{name}"
        dir_exists = os.path.exists(os.path.join(ROOT_DIR, folder))
        status = "✅ 已提取完成" if dir_exists else "⏳ 待處理"
        link = f"[{name}目錄]({folder}/{name}_目錄.md)" if dir_exists else name
        
        if int(no) == 40:
            lines.append("\n## ✝️ 新約聖經 (27 卷)\n\n")
            lines.append("| 編號 | 經卷名稱 | 經卷目錄連結 | 狀態 |\n")
            lines.append("| :--- | :--- | :--- | :--- |\n")
            
        lines.append(f"| `{no}` | **{name}** | {link} | {status} |\n")
        
    with open(global_idx_path, 'w', encoding='utf-8') as f:
        f.write("".join(lines))
    print(f"\n[+] 全本聖經總目錄已更新：全本聖經_總目錄.md")

def main():
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
        
    target_indices = []
    if len(sys.argv) == 3 and sys.argv[1].isdigit() and sys.argv[2].isdigit():
        start_idx = int(sys.argv[1])
        end_idx = int(sys.argv[2])
        target_indices = list(range(start_idx, end_idx + 1))
    elif len(sys.argv) > 1:
        target_indices = [int(x) for x in sys.argv[1:] if x.isdigit()]
    else:
        target_indices = list(range(1, 67))
        
    print(f"[*] 準備依序提取 {len(target_indices)} 卷經卷: {target_indices}")
    
    for count, idx in enumerate(target_indices, 1):
        if idx < 1 or idx > len(catalog):
            continue
        book_info = catalog[idx - 1]
        print(f"\n>>> [{count}/{len(target_indices)}] 處理進度：第 {book_info['no']} 卷 《{book_info['name']}》 <<<")
        try:
            process_book(book_info)
        except Exception as e:
            print(f"[ERROR] 處理《{book_info['name']}》時發生錯誤: {e}")
        # Update global index after each book
        update_global_bible_index(catalog)
        time.sleep(0.5)

    print("\n=======================================================")
    print("[SUCCESS] 指定經卷全部提取與轉換完成！")
    print("=======================================================")

if __name__ == '__main__':
    main()

