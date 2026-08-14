#!/usr/bin/env python3
"""
Step 1: ウェブ教科書HTML → 節単位の構造JSON

ソースは ktwvai のウェブ教科書のみ（material/ の公式テキストOCRは使わない）。
教科書側の意味づけ済みブロック（point-box / law-box / pitfall-box / case-box /
figure.comic / table.timeline）を、そのままスライドの素になる形で取り出す。

依存なし（標準ライブラリの html.parser だけ）。

使い方:
  python3 01_extract_outline.py                    # 2級・3級すべて
  python3 01_extract_outline.py --level 2kyu       # 級を絞る
  python3 01_extract_outline.py --chapter 1        # 章を絞る
  python3 01_extract_outline.py --level 2kyu --chapter 1 --stats
"""

import argparse
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

TEXTBOOK_ROOT = Path(__file__).parent.parent / "textbook"
OUT_DIR = Path(__file__).parent / "out" / "outline"

VOID = {"br", "img", "hr", "meta", "link", "input", "source", "area", "base", "col"}

# 教科書のボックス class → 内部種別
BOX_TYPES = {
    "point-box": "point",      # 📌 押さえるポイント  → まとめスライド
    "law-box": "law",          # 📋 制度・基準        → 制度カード
    "pitfall-box": "pitfall",  # 🔍 まちがえやすい     → ✕/○ 対比スライド
    "case-box": "case",        # 📝 暮らしの場面      → 事例スライド
}


# ---------------------------------------------------------------- DOM

class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        self.parent = parent

    def cls(self):
        return self.attrs.get("class", "").split()

    def text(self):
        """子孫のテキストを連結（空白は正規化）"""
        out = []
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            elif c.tag == "br":
                out.append(" ")
            else:
                out.append(c.text())
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def find_all(self, tag=None, cls=None):
        hits = []
        for c in self.children:
            if isinstance(c, str):
                continue
            if (tag is None or c.tag == tag) and (cls is None or cls in c.cls()):
                hits.append(c)
            hits.extend(c.find_all(tag, cls))
        return hits

    def find(self, tag=None, cls=None):
        hits = self.find_all(tag, cls)
        return hits[0] if hits else None


class DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, dict(attrs), self.cur))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # 同名の祖先を探して、そこまで巻き戻す（閉じ忘れに耐える）
        node = self.cur
        while node is not None and node is not self.root and node.tag != tag:
            node = node.parent
        if node is None or node is self.root:
            # 対応する開始タグが無い迷子の閉じタグ。無視する。
            # （ここで cur を root に戻すと、以降の要素が article の外に出て
            #   節がまるごと取りこぼされる）
            return
        self.cur = node.parent or self.root

    def handle_data(self, data):
        if data.strip():
            self.cur.children.append(data)
        elif data:
            self.cur.children.append(" ")


# ---------------------------------------------------------------- 抽出

def collect_terms(node):
    """強調語を拾う。term=重要語（オレンジ）/ term-x=否定・誤り（赤）"""
    return (
        [t.text() for t in node.find_all("span", "term")],
        [t.text() for t in node.find_all("span", "term-x")],
    )


def para_block(node):
    terms, terms_x = collect_terms(node)
    return {"type": "p", "text": node.text(), "terms": terms, "terms_x": terms_x}


def box_block(node, kind):
    h4 = node.find("h4")
    heading = h4.text() if h4 else ""
    terms, terms_x = collect_terms(node)
    block = {"type": kind, "heading": heading, "terms": terms, "terms_x": terms_x}

    if kind == "law":
        # law-box は <span class="article"> の箇条書き。<b> が見出し語になっている
        articles = []
        for a in node.find_all("span", "article"):
            b = a.find("b")
            label = b.text() if b else ""
            full = a.text()
            body = full[len(label):].lstrip("：: ") if label and full.startswith(label) else full
            articles.append({"label": label, "text": body})
        block["articles"] = articles
    else:
        block["paras"] = [p.text() for p in node.find_all("p")]

    return block


def figure_block(node):
    img = node.find("img")
    ftitle = node.find("span", "ftitle")
    cap = node.find("figcaption")
    caption = cap.text() if cap else ""
    title = ftitle.text() if ftitle else ""
    if title and caption.startswith(title):
        caption = caption[len(title):].strip()
    return {
        "type": "figure",
        "src": (img.attrs.get("src", "") if img else ""),
        "alt": (img.attrs.get("alt", "") if img else ""),
        "ftitle": title,
        "caption": caption,
    }


def table_block(node):
    head = [th.text() for th in node.find_all("th")]
    rows = []
    tbody = node.find("tbody") or node
    for tr in tbody.find_all("tr"):
        cells = [td.text() for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    return {"type": "table", "head": head, "rows": rows}


def walk_blocks(container):
    """要素の直下の子を、出現順のブロック列にする"""
    blocks = []
    for c in container.children:
        if isinstance(c, str):
            continue
        classes = c.cls()
        if c.tag == "h3":
            blocks.append({"type": "h3", "text": c.text()})
        elif c.tag == "h4":
            blocks.append({"type": "h4", "text": c.text()})
        elif c.tag == "p":
            blocks.append(para_block(c))
        elif c.tag == "figure" and "comic" in classes:
            blocks.append(figure_block(c))
        elif c.tag == "table":
            blocks.append(table_block(c))
        elif c.tag == "ul" or c.tag == "ol":
            items = [li.text() for li in c.find_all("li")]
            blocks.append({"type": "list", "ordered": c.tag == "ol", "items": items})
        elif c.tag == "div":
            for cname, kind in BOX_TYPES.items():
                if cname in classes:
                    blocks.append(box_block(c, kind))
                    break
    return blocks


def parse_chapter(path, level):
    html = path.read_text(encoding="utf-8")
    dom = DOMBuilder()
    dom.feed(html)
    root = dom.root

    hero = root.find("section", "page-hero")
    h1 = hero.find("h1") if hero else None
    sub = h1.find("span", "sub") if h1 else None
    title_full = h1.text() if h1 else ""
    sub_text = sub.text() if sub else ""
    title = title_full[: -len(sub_text)].strip() if sub_text and title_full.endswith(sub_text) else title_full
    kicker = hero.find("div", "kicker").text() if (hero and hero.find("div", "kicker")) else ""
    lead = hero.find("p", "lead").text() if (hero and hero.find("p", "lead")) else ""

    m = re.search(r"第\s*(\d+)\s*章", kicker) or re.search(r"第\s*(\d+)\s*章", title_full)
    ch_num = int(m.group(1)) if m else int(re.sub(r"\D", "", path.parent.name) or 0)

    article = root.find("article", "article")
    intro_fig = None
    sections = []
    warnings = []
    strays = {}

    # article 直下を出現順に走査する。
    # 教科書HTMLに余分な </section> が混ざっている章（2kyu ch4 / ch7）があり、
    # 節が途中で閉じて残りが article 直下にこぼれる。こぼれた分は
    # 直前の節の続きとして拾い直す（取りこぼし防止）。
    for c in (article.children if article else []):
        if isinstance(c, str):
            continue

        if c.tag == "section" and re.fullmatch(r"s\d+", c.attrs.get("id", "") or ""):
            sid = c.attrs["id"]
            h2 = c.find("h2")
            if h2 is None:
                warnings.append(f"{sid}: h2 が無い")
                continue
            chnum_span = h2.find("span", "ch-num")
            s_label = chnum_span.text() if chnum_span else ""
            s_title = h2.text()
            if s_label and s_title.startswith(s_label):
                s_title = s_title[len(s_label):].strip()
            sections.append({
                "num": int(re.sub(r"\D", "", sid)),
                "id": sid,
                "title": s_title,
                "blocks": walk_blocks(c),
            })
            continue

        # 節の外にある要素
        if c.tag == "figure" and "comic" in c.cls():
            if not sections:
                intro_fig = figure_block(c)          # 章の導入イラスト
                continue
        wrap = Node("#wrap")
        wrap.children = [c]
        stray = walk_blocks(wrap)
        if stray:
            if sections:
                sections[-1]["blocks"].extend(stray)
                strays.setdefault(sections[-1]["id"], []).extend(b["type"] for b in stray)
            else:
                strays.setdefault("(節の前)", []).extend(b["type"] for b in stray)

    for sid, types in strays.items():
        tally = ", ".join(f"{t}×{types.count(t)}" for t in dict.fromkeys(types))
        warnings.append(
            f"教科書HTMLに余分な </section> あり: {sid} の外に {len(types)} ブロック "
            f"({tally}) → {sid} の続きとして取り込んだ"
        )

    return {
        "warnings": warnings,
        "level": level,
        "source": str(path),
        "chapter": {
            "num": ch_num,
            "dir": path.parent.name,
            "title": title,
            "sub": sub_text.lstrip("— ").strip(),
            "kicker": kicker,
            "lead": lead,
            "total_sections": len(sections),
            "intro_figure": intro_fig,
        },
        "sections": sections,
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=["2kyu", "3kyu", "hr"], action="append")
    ap.add_argument("--chapter", type=int, action="append")
    ap.add_argument("--stats", action="store_true", help="ブロック種別の内訳を表示")
    args = ap.parse_args()

    levels = args.level or ["2kyu", "3kyu"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    grand = {}
    for level in levels:
        chapters = sorted(
            (TEXTBOOK_ROOT / level).glob("ch*/index.html"),
            key=lambda p: int(re.sub(r"\D", "", p.parent.name) or 0),
        )
        for path in chapters:
            num = int(re.sub(r"\D", "", path.parent.name) or 0)
            if args.chapter and num not in args.chapter:
                continue
            data = parse_chapter(path, level)
            out = OUT_DIR / f"{level}_ch{num:02d}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            counts = {}
            chars = 0
            for s in data["sections"]:
                for b in s["blocks"]:
                    counts[b["type"]] = counts.get(b["type"], 0) + 1
                    chars += len(b.get("text", "")) + sum(len(x) for x in b.get("paras", []))
            grand.setdefault(level, {"sections": 0, "chars": 0, "counts": {}})
            grand[level]["sections"] += len(data["sections"])
            grand[level]["chars"] += chars
            for k, v in counts.items():
                grand[level]["counts"][k] = grand[level]["counts"].get(k, 0) + v

            print(f"{level} ch{num:<2} {data['chapter']['title'][:22]:24s} "
                  f"節{len(data['sections'])}  {chars:>6,}字  → {out.name}")
            if args.stats:
                print("        " + "  ".join(f"{k}:{v}" for k, v in sorted(counts.items())))
            for w in data["warnings"]:
                print(f"        ⚠ {w}")

            # 取りこぼし検査: 生HTMLのブロック数と一致しているか
            raw = path.read_text(encoding="utf-8")
            for cname, kind in BOX_TYPES.items():
                n_raw = raw.count(f'class="{cname}"')
                n_got = counts.get(kind, 0)
                if n_raw != n_got:
                    print(f"        ✗ {kind}: HTML {n_raw} 件 / 抽出 {n_got} 件 — 差分あり")

    print()
    for level, g in grand.items():
        print(f"[{level}] 節 {g['sections']}  本文 {g['chars']:,}字")
        print("        " + "  ".join(f"{k}:{v}" for k, v in sorted(g['counts'].items())))


if __name__ == "__main__":
    main()
