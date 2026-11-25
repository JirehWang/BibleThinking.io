import urllib.request
import json
import os
import re
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

PDF_DIR = r'd:\Bible\啟示錄_電子書_PDF'

# 1. Fetch 66index-T.htm to get the exact BOOK_CONFIG
req = urllib.request.Request('https://www.ccbiblestudy.org/New%20Testament/66Rev/66index-T.htm', headers=headers)
html = urllib.request.urlopen(req).read().decode('utf-8')

# Extract books array from BOOK_CONFIG
match = re.search(r'"books":\s*(\[[\s\S]*?\])\s*};', html)
if match:
    books_str = match.group(1)
    # Remove JS single-line comments in JSON
    books_str = re.sub(r'//.*', '', books_str)
    # Fix trailing commas if any
    books_str = re.sub(r',\s*\]', ']', books_str)
    books = json.loads(books_str)
else:
    # Fallback list if regex fails
    books = [
        {"no":"66BT01", "title":"啟示錄註解", "author":"黃迦勒", "href":"66BT01.pdf"},
        {"no":"66BT02", "title":"啟示錄要義", "author":"黃共明", "href":"66BT02.pdf"},
        {"no":"66BT03", "title":"啟示錄要義", "author":"倪柝聲", "href":"66BT03.pdf"},
        {"no":"66BT04", "title":"啟示錄釋義", "author":"倪柝聲", "href":"66BT04.pdf"},
        {"no":"66BT05", "title":"啟示錄信息", "author":"倪柝聲", "href":"66BT05.pdf"},
        {"no":"66BT06", "title":"聖靈所說的話", "author":"倪柝聲", "href":"66BT06.pdf"},
        {"no":"66BT07", "title":"教會的正統", "author":"倪柝聲", "href":"66BT07.pdf"},
        {"no":"66BT08", "title":"耶穌基督的見證", "author":"江守道", "href":"66BT08.pdf"},
        {"no":"66BT09", "title":"聖靈向眾教會所說的話", "author":"江守道", "href":"66BT09.pdf"},
        {"no":"66BT10", "title":"啟示錄透視", "author":"江守道", "href":"66BT10.pdf"},
        {"no":"66BT11", "title":"聖城新耶路撒冷", "author":"史百克", "href":"66BT11.pdf"},
        {"no":"66BT12", "title":"羔羊的跟隨者", "author":"史百克", "href":"66BT12.pdf"},
        {"no":"66BT15", "title":"啟示錄簡介", "author":"楊震宇", "href":"66BT15.pdf"},
        {"no":"66BT16", "title":"啟示錄每日靈糧套餐", "author":"楊震宇", "href":"66BT16.pdf"},
        {"no":"66BT17", "title":"啟示錄鳥瞰", "author":"楊震宇", "href":"66BT17.pdf"},
        {"no":"66BT18", "title":"啟示錄讀經課程", "author":"楊震宇", "href":"66BT18.pdf"},
        {"no":"66BT19", "title":"啟示錄讀經劄記", "author":"王國顯", "href":"66BT19.pdf"},
        {"no":"66BT20", "title":"啟示錄中的七個教會", "author":"陳終道", "href":"66BT20.pdf"},
        {"no":"66BT21", "title":"老底嘉教會－中年肥胖", "author":"藍培德", "href":"66BT21.pdf"},
        {"no":"66BT22", "title":"天開了", "author":"朱有榮", "href":"66BT22.pdf"},
        {"no":"66BT23", "title":"新約《啟示錄》精華", "author":"漆立平", "href":"66BT23.pdf"},
        {"no":"66BT24", "title":"讀啟示錄", "author":"黃得恩", "href":"66BT24.pdf"},
        {"no":"66BT25", "title":"啟示錄註解", "author":"大陸老傳道人", "href":"66BT25.pdf"},
        {"no":"66BT26", "title":"啟示錄竅要", "author":"徐仲潔", "href":"66BT26.pdf"},
        {"no":"66BT27", "title":"啟示錄簡介（上冊）", "author":"陳本偉", "href":"66BT27.pdf"},
        {"no":"66BT28", "title":"啟示錄簡介（下冊）", "author":"陳本偉", "href":"66BT28.pdf"},
        {"no":"66BT29", "title":"啟示錄要義", "author":"林獻羔", "href":"66BT29.pdf"},
        {"no":"66BT30", "title":"啟示錄讀經資料", "author":"楊震宇", "href":"66BT30.pdf"}
    ]

os.makedirs(PDF_DIR, exist_ok=True)

download_list = []
for b in books:
    href = b.get('href')
    status = b.get('status')
    if not href or status == 'not-ready':
        continue
    no = b.get('no', '')
    title = b.get('title', '')
    author = b.get('author', '')
    
    # Clean filename
    author_str = f"_{author}" if author else ""
    # Extract index number from no, e.g. 66BT01 -> 01
    idx_str = re.sub(r'^\d+BT', '', no)
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    filename = f"{idx_str}_{safe_title}{author_str}.pdf"
    
    url = f"https://www.ccbiblestudy.org/New%20Testament/66Rev/{href}"
    download_list.append((no, title, author, url, filename))

print(f"Total valid PDF books to download: {len(download_list)}")

success_count = 0
total_bytes = 0
index_entries = []

for no, title, author, url, filename in download_list:
    dest_path = os.path.join(PDF_DIR, filename)
    print(f"[*] Downloading [{no}] {title} ({author})...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as res:
            pdf_data = res.read()
            with open(dest_path, 'wb') as fp:
                fp.write(pdf_data)
            size_mb = len(pdf_data) / (1024 * 1024)
            total_bytes += len(pdf_data)
            success_count += 1
            print(f"    [+] Saved: {filename} ({size_mb:.2f} MB)")
            index_entries.append((no, title, author, filename, f"{size_mb:.2f} MB"))
    except Exception as e:
        print(f"    [-] Failed to download {url}: {e}")
    time.sleep(0.2)

# Generate README.md in PDF folder
readme_lines = [
    "# 📚 啟示錄 電子書專題全集 (PDF)\n\n",
    "> 資料來源：[華人基督徒查經資料網站 (ccbiblestudy.org)](https://www.ccbiblestudy.org/)\n",
    f"> 總計下載：**{success_count} 本權威電子書**（總大小：**{total_bytes / (1024*1024):.2f} MB**）\n\n",
    "| 編號 | 書名 | 作者 | 檔案名稱 | 檔案大小 |\n",
    "| :--- | :--- | :--- | :--- | :--- |\n"
]

for no, title, author, filename, size_str in index_entries:
    author_display = author if author else "—"
    readme_lines.append(f"| `{no}` | **{title}** | {author_display} | [{filename}]({filename}) | {size_str} |\n")

with open(os.path.join(PDF_DIR, "README.md"), 'w', encoding='utf-8') as f:
    f.write("".join(readme_lines))

print(f"\n[SUCCESS] Downloaded {success_count} PDF books ({total_bytes / (1024*1024):.2f} MB) into {PDF_DIR}")
