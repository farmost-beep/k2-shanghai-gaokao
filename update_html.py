#!/usr/bin/env python3
"""从MD解析VIX条目自动更新index.html表格内容 + 日期（高考版）。

用法: python3 update_html.py
"""
import re, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))

def parse_md_vix_items(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        md = f.read()

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', md[:200])
    date_str = date_match.group(1) if date_match else None

    sections = re.split(r'^## ', md, flags=re.MULTILINE)
    items = []
    for sec in sections:
        if not sec.strip():
            continue
        lines = sec.strip().split('\n')
        title = lines[0].strip()

        if '本周核心判断' in title or '核心框架' in title:
            continue

        vix_match = re.search(r'\*\*VIX评分[：:]\s*(\d+)\*\*', sec)
        if not vix_match:
            continue
        vix = int(vix_match.group(1))

        # Find data table
        data_summary = ""
        in_table = False
        for line in lines:
            if '|' in line and line.strip().startswith('|'):
                cells = [c.strip() for c in line.strip().split('|') if c.strip()]
                if len(cells) >= 2 and not cells[0].startswith('—') and not any('指标' in c for c in cells):
                    data_summary = cells[1] if len(cells) > 1 else ""
                    break

        action = ""
        action_match = re.search(r'(?:核心行动|建议|方向)[：:]\s*([^\n]+)', sec[sec.find(str(vix)):])
        if action_match:
            action = action_match.group(1).strip()[:60]

        items.append((vix, title, data_summary, action))
    return items, date_str


def html_vix_row(vix, title, data, action, bg):
    color = "#c0392b" if vix >= 80 else "#e67e22"
    return f'''      <tr style="background:{bg}">
        <td style="padding:6px 8px;color:{color};font-weight:700;font-size:13px">{vix}</td>
        <td style="padding:6px 8px"><span style="background:#e8f5e9;color:#2e7d32;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700">高</span></td>
        <td style="padding:6px 8px;font-weight:600">{title}</td>
        <td style="padding:6px 8px;font-size:11px">{data}</td>
        <td style="padding:6px 8px;font-size:11px;color:{color}">{action}</td>
      </tr>'''


def update_html(html_path, md_path):
    items, date_str = parse_md_vix_items(md_path)
    if not items:
        print(f"❌ 未解析到VIX条目: {md_path}")
        return False

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    if date_str:
        date_display = date_str.replace('-', '年', 1).replace('-', '月', 1) + '日'
        html = re.sub(r'提供日期：\d{4}年\d{1,2}月\d{1,2}日', f'提供日期：{date_display}', html)

    new_rows = '\n'.join([
        html_vix_row(vix, title, data, action, "#fff" if i % 2 == 0 else "#fafafa")
        for i, (vix, title, data, action) in enumerate(items[:6])
    ])

    pattern = r'(<tr style="background:(?:var\(--ustc\)|#[a-f0-9]+);color:#fff">.*?</tr>\s*)(.*?)(\s*</table>)'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        header = match.group(1)
        html = html[:match.start(1)] + header + '\n' + new_rows + '\n' + match.group(3) + html[match.end(3):]
        print(f"✅ 已更新 {len(items)} 条VIX条目, 日期={date_str}")
    else:
        print("⚠️ 未找到表格结构")
        return False

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return True


def main():
    md_path = os.path.join(DIR, "高考择校高价值信息清单.md")
    html_path = os.path.join(DIR, "index.html")
    if not os.path.exists(md_path):
        print(f"❌ 未找到MD: {md_path}")
        sys.exit(1)
    if update_html(html_path, md_path):
        print(f"✅ {html_path} 更新完成")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
