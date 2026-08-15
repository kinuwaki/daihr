#!/usr/bin/env python3
"""
Step 4: 台本JSON → スライドPNG（1920x1080）

Playwright は入れず、macOS に既にある Google Chrome の headless を使う。
1カット = PNG 1枚。箇条書きは「1行ずつ増える」状態を別カットとして持っているので、
静止画の連続だけでアニメーションに見える（動画エンコードの入れ子が不要）。

使い方:
  python3 04_render_slides.py --level 2kyu --chapter 1 --section 1
  python3 04_render_slides.py --level 2kyu --chapter 1 --section 1 --limit 20
  python3 04_render_slides.py --level 2kyu --chapter 1 --section 1 --html-only
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT_DIR = HERE / "out" / "script"
SLIDE_DIR = HERE / "out" / "slides"
CSS = HERE / "templates" / "slide.css"

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H = 1920, 1080


# ------------------------------------------------------------ HTML 組み立て

def esc(t):
    # LLM が文字列のつもりの項目に配列を返すことがある（表のヘッダ行を
    # heading に入れてしまう等）。1本のために全体を止めたくないので、
    # ここで文字列に均してから逃がす。
    if isinstance(t, (list, tuple)):
        t = "／".join(str(x) for x in t if x)
    elif t is not None and not isinstance(t, str):
        t = str(t)
    return html.escape(t or "", quote=False)


def mark_terms(text, terms, terms_x):
    """本文中のキーワードを教科書と同じ色で強調する。
    長い語から置換しないと部分一致で壊れるので、長さ降順で処理する。"""
    out = esc(text)
    marks = [(t, "term-x") for t in (terms_x or [])] + [(t, "term") for t in (terms or [])]
    marks = [(t, c) for t, c in marks if t]
    marks.sort(key=lambda x: -len(x[0]))
    for i, (t, cls) in enumerate(marks):
        token = f"\x00{i}\x00"
        out = out.replace(esc(t), token, 1)
    for i, (t, cls) in enumerate(marks):
        out = out.replace(f"\x00{i}\x00", f'<span class="{cls}">{esc(t)}</span>')
    return out


def body_class(text):
    n = len(text)
    if n > 170:
        return "body-text long"
    if n < 70:
        return "body-text short"
    return "body-text"


def bullets_html(items, focus=None, labels=True, upto=None):
    """upto を渡すと、そこまでの項目だけを点灯させる（段階表示）。
    dict の "x": True は誤り・否定の要点なので赤で出す。"""
    rows = []
    for i, it in enumerate(items):
        is_x = False
        if isinstance(it, dict):
            label, body = it.get("label", ""), it.get("text", "")
            is_x = bool(it.get("x"))
            inner = (f'<span class="label">{esc(label)}</span>　{esc(body)}'
                     if label and labels else esc(body or label))
        else:
            inner = esc(it)
        lit = True if upto is None else i <= upto
        cls = ("on" if lit else "") + (" focus" if focus == i else "") + (" x" if is_x else "")
        rows.append(f'<li class="{cls}"><span class="num">{i+1}</span>'
                    f'<span>{inner}</span></li>')
    return f'<ul class="bullets">{"".join(rows)}</ul>'


def card(kind, badge, title, inner, tight=False):
    return (f'<div class="card card-{kind}{" tight" if tight else ""}">'
            f'<h3><span class="badge">{badge}</span>{esc(title)}</h3>{inner}</div>')


BADGE = {"law": "📐", "pitfall": "⚠️", "point": "📌", "case": "💡"}  # kikuhr: 設計原則📐 / 落とし穴⚠️ / 実例💡


def stage_html(cut, img_base):
    k = cut["kind"]
    d = cut["display"]

    if k == "title":
        return (
            '<div class="stage title-slide">'
            f'<div class="kicker">{esc(d["section"])}</div>'
            f'<div class="chapter">{esc(d["chapter"])}</div>'
            '<div class="rule"></div>'
            f'<h1>{esc(d["title"])}</h1>'
            + (f'<div class="sub">{esc(d["chapter_sub"])}</div>' if d.get("chapter_sub") else "")
            + '</div>')

    if k == "goals":
        return ('<div class="stage heading-slide">'
                '<div class="bar"></div>'
                f'<h2>{esc(d["title"])}</h2>'
                + bullets_html(d["items"], labels=False) + '</div>')

    if k == "heading":
        return ('<div class="stage heading-slide">'
                '<div class="bar"></div>'
                f'<h2>{esc(d["title"])}</h2></div>')

    if k == "question":
        # 論点の入口に置く問いスライド。答えの前に「間」を作るのが役目なので、
        # 画面には問いだけを大きく出す。
        return ('<div class="stage q-slide">'
                '<div class="q-mark">?</div>'
                f'<div class="q-text">{esc(d.get("text") or "")}</div>'
                '</div>')

    if k == "number":
        # 覚えてほしい数値・条文番号を画面いっぱいに出す
        return ('<div class="stage n-slide">'
                f'<div class="n-value">{esc(d.get("value") or "")}</div>'
                + (f'<div class="n-label">{esc(d["label"])}</div>' if d.get("label") else "")
                + '</div>')

    if k == "talk":
        # 授業プレゼン型（02b・LLM生成）のスライド。
        # 画面は要約された要点、音声は話し言葉。両者は別物なので、
        # ここに読み上げ文は出さない。要点は focus まで点灯させる。
        focus = d.get("focus", 0)
        rows = []
        for i, b in enumerate(d.get("bullets", [])):
            lit = i <= focus
            cls = "tk-line" + (" now" if i == focus else (" past" if lit else " ahead"))
            rows.append(f'<div class="{cls}"><span class="mk"></span>'
                        f'<span class="t">{esc(b)}</span></div>')
        head = esc(d.get("head") or "")
        return ('<div class="stage tk">'
                + (f'<div class="tk-head">{head}</div>' if head else "")
                + f'<div class="tk-lines">{"".join(rows)}</div>'
                '</div>')

    if k == "summary":
        return (f'<div class="stage">'
                f'{card("point", "🗂", d["title"], bullets_html(d.get("items", []), labels=False), tight=True)}'
                '</div>')

    if k == "figure":
        src = (Path(img_base) / d["src"]).as_uri() if d.get("src") else ""
        return ('<div class="stage figure-slide">'
                + (f'<img src="{src}">' if src else "")
                + (f'<div class="ftitle">{esc(d["ftitle"])}</div>' if d.get("ftitle") else "")
                + (f'<div class="caption">{esc(d["caption"])}</div>' if d.get("caption") else "")
                + '</div>')

    if k in ("case_lead", "case"):
        inner = f'<div class="text">{esc(d.get("text",""))}</div>' if d.get("text") else ""
        return f'<div class="stage">{card("case", BADGE["case"], d["title"], inner)}</div>'

    if k in ("law_lead", "law"):
        inner = bullets_html(d.get("items", []), d.get("focus"))
        return (f'<div class="stage">'
                f'{card("law", BADGE["law"], d["title"], inner, tight=True)}</div>')

    if k == "pitfall_lead":
        wrong, right = d.get("wrong") or [], d.get("right") or []
        # ✕と○が両方あるときだけ対比にする。片側しか無いのに二段組にすると
        # 空の欄ができて意味が伝わらない
        if wrong and right:
            cols = ('<div class="col x"><div class="mark">✕</div>'
                    '<div class="lead">まちがい</div>'
                    + "".join(f'<div class="item">{esc(w)}</div>' for w in wrong)
                    + '</div>'
                    '<div class="col o"><div class="mark">○</div>'
                    '<div class="lead">正しい</div>'
                    + "".join(f'<div class="item">{esc(r)}</div>' for r in right)
                    + '</div>')
            return (f'<div class="stage"><div class="card card-pitfall">'
                    f'<h3><span class="badge">{BADGE["pitfall"]}</span>{esc(d["title"])}</h3>'
                    f'<div class="compare">{cols}</div></div></div>')
        keys = wrong or right
        if keys:
            lead = "ここがまちがいのもと" if wrong else "ここを押さえる"
            cls = "term-x" if wrong else "term"
            inner = (f'<div class="chips-lead">{lead}</div><div class="chips">'
                     + "".join(f'<span class="chip {cls}">{esc(x)}</span>' for x in keys)
                     + '</div>')
            return (f'<div class="stage">'
                    f'{card("pitfall", BADGE["pitfall"], d["title"], inner)}</div>')
        return (f'<div class="stage">'
                f'{card("pitfall", BADGE["pitfall"], d["title"], "")}</div>')

    if k == "pitfall":
        t = d.get("text", "")
        inner = (f'<div class="text">'
                 f'{mark_terms(t, d.get("right"), d.get("wrong"))}</div>')
        return (f'<div class="stage">'
                f'{card("pitfall", BADGE["pitfall"], d["title"], inner, tight=True)}</div>')

    if k in ("point_lead", "point_intro", "point"):
        if d.get("items"):
            inner = bullets_html(d["items"], d.get("focus"), labels=False)
        else:
            inner = ""
        return (f'<div class="stage">'
                f'{card("point", BADGE["point"], d["title"], inner, tight=True)}</div>')

    if k == "table":
        head = "".join(f"<th>{esc(h)}</th>" for h in d.get("head", []))
        rows = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>"
                       for r in d.get("rows", []))
        thead = f"<thead><tr>{head}</tr></thead>" if head else ""
        return f'<div class="stage"><table>{thead}<tbody>{rows}</tbody></table></div>'

    if k == "list":
        return (f'<div class="stage">'
                f'{bullets_html(d.get("items", []), d.get("focus"), labels=False)}</div>')

    if k == "student":
        return ('<div class="stage dialogue">'
                f'<div class="bubble">{esc(d["bubble"])}</div>'
                '<div class="who"><div class="chip">生徒</div>質問</div>'
                '</div>')

    if k == "outro":
        return ('<div class="stage outro-slide">'
                f'<h2>{esc(d["title"])}</h2>'
                f'<div class="app">{esc(d["app"])}</div>'
                '<div class="note">実装の詳細はリポジトリのコードを参照してください。</div>'
                f'<div class="credits">{"<br>".join(esc(c) for c in d["credits"])}</div>'
                '</div>')

    # 未知の種別は本文扱いにする（落とさない）
    return (f'<div class="stage"><div class="body-text">'
            f'{esc(cut.get("subtitle",""))}</div></div>')


def page_html(cut, meta, css_href, img_base):
    ch = f'第{meta["chapter"]}章 {meta["chapter_title"]}'
    sec = f'第{meta["section"]}節 {meta["section_title"]}'
    top = ('<div class="topbar">'
           f'<span class="ch">{esc(ch)}</span>'
           '<span class="sep">／</span>'
           f'<span>{esc(sec)}</span>'
           + (f'<span class="heading">{esc(cut["heading"])}</span>' if cut.get("heading") else "")
           + '</div>')
    foot = ('<div class="footer">'
            f'<span>{esc(meta["chapter_title"])}</span>'
            f'<span class="credit">{esc(" ／ ".join(meta["credits"]))}</span>'
            '</div>')
    # タイトルと終了スライドは上部バーを出さない
    if cut["kind"] in ("title", "outro"):
        top = ""
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="{css_href}"></head><body>'
            f'<div class="slide">{top}{stage_html(cut, img_base)}{foot}</div>'
            f'</body></html>')


# ------------------------------------------------------------ 描画

def render_png(html_path, png_path):
    cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-sandbox", "--force-device-scale-factor=1",
           f"--window-size={W},{H}", "--virtual-time-budget=3000",
           "--default-background-color=FFFDFAF6",
           f"--screenshot={png_path}", html_path.as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not Path(png_path).exists():
        raise RuntimeError(f"描画失敗: {html_path.name}\n{r.stderr[-600:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--section", type=int, required=True)
    ap.add_argument("--part", type=int, help="前編/後編に分割された節のパート番号（1,2,…）")
    ap.add_argument("--limit", type=int, help="先頭Nカットだけ描画（確認用）")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--only", type=int, action="append", help="カット番号を指定して描画")
    args = ap.parse_args()

    key = f"{args.level}_ch{args.chapter:02d}_s{args.section:02d}"
    if getattr(args, "part", None):
        key += f"p{args.part}"
    script_path = SCRIPT_DIR / f"{key}.json"
    if not script_path.exists():
        sys.exit(f"台本がありません: {script_path}")
    meta = json.loads(script_path.read_text(encoding="utf-8"))

    out = SLIDE_DIR / key
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(CSS, out / "slide.css")

    cuts = meta["cuts"]
    if args.only:
        cuts = [c for c in cuts if c["no"] in set(args.only)]
    elif args.limit:
        cuts = cuts[: args.limit]

    if not CHROME.exists() and not args.html_only:
        sys.exit(f"Chrome が見つかりません: {CHROME}")

    for i, cut in enumerate(cuts, 1):
        hp = out / f"cut{cut['no']:03d}.html"
        hp.write_text(page_html(cut, meta, "slide.css", meta["img_base"]),
                      encoding="utf-8")
        if args.html_only:
            continue
        pp = out / f"cut{cut['no']:03d}.png"
        render_png(hp, pp)
        print(f"  [{i}/{len(cuts)}] cut{cut['no']:03d} {cut['kind']:<13} "
              f"{cut['subtitle'][:34]}")

    print(f"\n{len(cuts)} カット → {out}")


if __name__ == "__main__":
    main()
