import fitz
import os
import glob
import re

PDF_DIR = r'd:\Bible\啟示錄_電子書_PDF'
MD_EBOOK_DIR = r'd:\Bible\啟示錄_電子書_MD'

os.makedirs(MD_EBOOK_DIR, exist_ok=True)

pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))

def clean_pdf_text_to_markdown(doc, book_title):
    md_lines = [f"# {book_title}\n\n", "> 格式：Markdown 數位文字重構版\n\n---\n\n"]
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text("text")
        if not text.strip():
            continue
            
        raw_lines = text.splitlines()
        page_lines = []
        for line in raw_lines:
            l = line.strip()
            if not l:
                continue
            # Filter page numbers or headers like "啟示錄註解 - Caleb Huang" or standalone page digits
            if re.match(r'^\d+$', l) or re.match(r'^第\s*\d+\s*頁$', l):
                continue
            if re.match(r'^[壹貳參肆伍陸柒捌玖拾]、', l):
                page_lines.append(f"\n## {l}\n")
            elif re.match(r'^[一二三四五六七八九十]+、', l):
                page_lines.append(f"\n### {l}\n")
            elif l.startswith('【') and '】' in l:
                page_lines.append(f"\n### {l}\n")
            elif l.startswith('第') and ('章' in l or '篇' in l) and len(l) < 20:
                page_lines.append(f"\n## {l}\n")
            elif l.startswith('〔') and '〕' in l:
                closing = l.find('〕')
                tag = l[:closing+1]
                content = l[closing+1:].strip()
                page_lines.append(f"> **{tag}** {content}\n")
            else:
                page_lines.append(f"{l}\n\n")
                
        md_lines.append("".join(page_lines))
        
    return "".join(md_lines)

total_pdf_size = 0
total_md_size = 0
converted_books = []

for pdf_file in pdf_files:
    pdf_size = os.path.getsize(pdf_file)
    total_pdf_size += pdf_size
    
    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    md_filename = f"{base_name}.md"
    md_path = os.path.join(MD_EBOOK_DIR, md_filename)
    
    doc = fitz.open(pdf_file)
    md_text = clean_pdf_text_to_markdown(doc, base_name)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_text)
        
    md_size = os.path.getsize(md_path)
    total_md_size += md_size
    reduction = 100 - (md_size / pdf_size * 100)
    converted_books.append((base_name, pdf_size, md_size, reduction))
    print(f"[*] {base_name}: {pdf_size/(1024*1024):.2f}MB -> {md_size/1024:.1f}KB ({reduction:.1f}% smaller)")

print(f"\n=== SUMMARY ===")
print(f"Total PDFs: {len(pdf_files)}")
print(f"Total PDF Size: {total_pdf_size / (1024*1024):.2f} MB")
print(f"Total MD Size: {total_md_size / (1024*1024):.2f} MB ({total_md_size / 1024:.1f} KB)")
print(f"Overall Space Saved: {100 - (total_md_size / total_pdf_size * 100):.1f}%")
