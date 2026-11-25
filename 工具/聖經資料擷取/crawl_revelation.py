import urllib.request
import re
import os
import time
import sys
from bs4 import BeautifulSoup

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

OUTPUT_DIR = r'd:\Bible\啟示錄'

def decode_html_bytes(raw_bytes):
    """
    Intelligently decode raw HTML bytes from ccbiblestudy.org.
    Handles pages encoded in Big5, Big5-HKSCS, CP950, GB18030, or UTF-8.
    """
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
            # Check for authentic Chinese characters in context
            if any(k in text for k in ['耶穌', '基督', '啟示錄', '約翰', '教會', '神', '使徒', '天使', '生命', '章', '註解', '拾穗', '綱目']):
                return text, enc
        except Exception:
            continue
            
    # Fallback with error substitution
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
    # Normalize Chinese punctuation spacing
    text = re.sub(r'【\s*([^】]+?)\s*】', r'【\1】', text)
    text = re.sub(r'〔\s*([^〕]+?)\s*〕', r'〔\1〕', text)
    text = re.sub(r'\(\s*([^)]+?)\s*\)', r'(\1)', text)
    text = re.sub(r'（\s*([^）]+?)\s*）', r'（\1）', text)
    text = re.sub(r'「\s*([^」]+?)\s*」', r'「\1」', text)
    text = re.sub(r'『\s*([^』]+?)\s*』', r'『\1』', text)
    text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
    return text

def parse_html_to_markdown(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup.find_all(['script', 'style', 'head']):
        tag.decompose()
        
    tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'])
    md_lines = []
    
    for tag in tags:
        if tag.name not in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'] and tag.find(['p', 'h1', 'h2', 'h3']):
            continue
            
        text = clean_paragraph_text(tag)
        if not text:
            continue
        if '返回首頁' in text and '返回' in text:
            continue
            
        # Structure headings & blockquotes
        if re.match(r'^【啟[一二三四五六七八九十\d]+', text):
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
        except Exception as e:
            if i == retries - 1:
                return None
            time.sleep(1)
    return None

def process_chapter(ch_num):
    ch_str = f"{ch_num:02d}"
    if ch_num == 0:
        ch_title = "啟示錄 導論與提要"
        filename = "啟示錄_第00章_導論與提要.md"
    elif ch_num == 23:
        ch_title = "啟示錄 全書綜合靈訓"
        filename = "啟示錄_第23章_綜合靈訓.md"
    else:
        ch_title = f"啟示錄 第 {ch_num} 章"
        filename = f"啟示錄_第{ch_str}章.md"
        
    print(f"[*] Processing {ch_title}...")
    
    # Header Navigation
    nav_links = ["[目錄](啟示錄_目錄.md)"]
    if ch_num > 0:
        prev_str = f"{ch_num-1:02d}"
        prev_file = "啟示錄_第00章_導論與提要.md" if ch_num - 1 == 0 else f"啟示錄_第{prev_str}章.md"
        nav_links.append(f"[上一章 ({ch_num-1})]({prev_file})")
    if ch_num < 23:
        next_str = f"{ch_num+1:02d}"
        next_file = "啟示錄_第23章_綜合靈訓.md" if ch_num + 1 == 23 else f"啟示錄_第{next_str}章.md"
        nav_links.append(f"[下一章 ({ch_num+1})]({next_file})")
        
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
        url = f"https://www.ccbiblestudy.org/New%20Testament/66Rev/66{code}{ch_str}.htm"
        html = fetch_and_decode_url(url)
        time.sleep(0.1) # Polite delay
        if html:
            section_md = parse_html_to_markdown(html)
            if section_md.strip():
                has_content = True
                doc.append(f"## {mod_title}\n\n")
                doc.append(section_md)
                doc.append("\n\n---\n\n")
                
    doc.append(f"\n\n{nav_bar}\n")
    
    if has_content:
        file_path = os.path.join(OUTPUT_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("".join(doc))
        print(f"    [+] Saved: {filename} ({os.path.getsize(file_path):,} bytes)")
    else:
        print(f"    [-] No content for {ch_title}")

def generate_index():
    index_path = os.path.join(OUTPUT_DIR, "啟示錄_目錄.md")
    lines = [
        "# 📖 啟示錄 查經與註解全書目錄\n\n",
        "> 本專題庫完整擷取自 **華人基督徒查經資料網站**，整合黃迦勒註解、歷代屬靈名家拾穗、例證、靈修信息與講章綱目。\n\n",
        "## 📑 章節清單\n\n",
        "| 章節 | 說明 | 連結 |\n",
        "| :--- | :--- | :--- |\n",
        "| **第 00 章** | 啟示錄導論、背景與全書提要 | [啟示錄_第00章_導論與提要.md](啟示錄_第00章_導論與提要.md) |\n"
    ]
    
    for i in range(1, 23):
        ch_str = f"{i:02d}"
        lines.append(f"| **第 {i:02d} 章** | 啟示錄第 {i} 章（註解 / 拾穗 / 例證 / 信息 / 綱目） | [啟示錄_第{ch_str}章.md](啟示錄_第{ch_str}章.md) |\n")
        
    lines.append("| **第 23 章** | 啟示錄全書總結與綜合靈訓 | [啟示錄_第23章_綜合靈訓.md](啟示錄_第23章_綜合靈訓.md) |\n\n")
    
    lines.append("## 📌 包含單元\n\n")
    lines.append("每一章 Markdown 檔案均結構化整合以下五大單元：\n")
    lines.append("1. **📖 壹、經文詳解與註解** (黃迦勒《基督徒文摘解經系列》逐節詳解)\n")
    lines.append("2. **🌾 貳、讀經拾穗** (各家解經名著精選)\n")
    lines.append("3. **💡 叁、例證故事** (相關屬靈見證與比喻例證)\n")
    lines.append("4. **🕊️ 肆、靈修信息** (生命讀經與靈修默想)\n")
    lines.append("5. **📑 伍、講章綱目** (主日講道與查經教導大綱)\n")
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("".join(lines))
    print(f"[+] Master index created: 啟示錄_目錄.md")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_time = time.time()
    for ch in range(0, 24):
        process_chapter(ch)
    generate_index()
    elapsed = time.time() - start_time
    print(f"[SUCCESS] All chapters processed in {elapsed:.2f}s")

if __name__ == '__main__':
    main()
