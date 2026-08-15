#!/usr/bin/env python3
"""
Step 3: 台本の機械チェック

音声を1本も作らずに、読み上げの問題を洗い出す。
VOICEVOX の /audio_query は「読み（kana）」を返すので、
**耳で聞かずに誤読を検出できる**。これをテストとして回す。

チェック内容:
  1. 記号の残存 — スラッシュ・波ダッシュ・丸数字・矢印など、辞書では直らないもの
  2. 読み辞書の効き — dict/yomi.json の各語が期待どおり読まれるか
  3. 難読語の掃き出し — 教科書キーワードの漢字熟語の読みを一覧化（新規レビュー用）
  4. 尺 — 1節が長すぎ／短すぎないか

使い方:
  python3 03_review_script.py                      # 1・2・4 を実行
  python3 03_review_script.py --check-readings     # 3 も実行（時間がかかる）
  python3 03_review_script.py --level 2kyu
"""

import argparse
import collections
import glob
import json
import re
from pathlib import Path

import vvx

HERE = Path(__file__).parent
SCRIPT_DIR = HERE / "out" / "script"
OUTLINE_DIR = HERE / "out" / "outline"

# 読み上げ文に残っていてはいけない記号
FORBIDDEN = {
    "/": "半角スラッシュ", "／": "全角スラッシュ",
    "〜": "波ダッシュ", "～": "全角チルダ",
    "%": "％記号", "％": "全角％",
    "—": "ダッシュ", "–": "ダッシュ", "―": "ダッシュ",
    "→": "矢印", "⇒": "矢印", "←": "矢印",
    "「": "かぎ括弧", "」": "かぎ括弧", "『": "二重括弧", "』": "二重括弧",
    "（": "全角括弧", "）": "全角括弧", "(": "半角括弧", ")": "半角括弧",
    "・": "中黒", "±": "プラマイ", "×": "かける記号", "≒": "ニアリー",
    "※": "注記", "①": "丸数字", "②": "丸数字", "③": "丸数字",
}

# 想定する1節の尺（分）
MIN_MINUTES, MAX_MINUTES = 5.0, 20.0


def load_scripts(levels):
    files = []
    for lv in levels:
        files += sorted(SCRIPT_DIR.glob(f"{lv}_ch*_s*.json"))
    return files


def check_symbols(files):
    print("── 1. 記号の残存 ──")
    hits = collections.Counter()
    samples = {}
    cuts = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        for c in d["cuts"]:
            cuts += 1
            speech = c["speech"]
            # 漢数字にはさまれた中黒は小数点（〇・三五）なので読み上げ上は正しい。
            # 並列の中黒だけを検出したいので、小数点は検査対象から外す。
            checked = re.sub(r"(?<=[〇一二三四五六七八九十])・(?=[〇一二三四五六七八九十])",
                             "", speech)
            for ch, label in FORBIDDEN.items():
                if ch in checked:
                    hits[label] += 1
                    samples.setdefault(label, (f.name, c["no"], c["speech"][:70]))
    print(f"   検査カット {cuts:,}")
    if not hits:
        print("   ✓ 問題記号なし")
    for label, n in hits.most_common():
        fn, no, ex = samples[label]
        print(f"   ✗ {label}: {n}件  例) {fn} cut{no}: {ex}")
    return cuts, sum(hits.values())


def check_yomi_dict():
    print("\n── 2. 読み辞書の効き ──")
    spec = json.loads(vvx.YOMI.read_text(encoding="utf-8"))
    added, updated = vvx.apply_yomi_dict()
    print(f"   辞書を反映: 新規{added} / 更新{updated}")
    bad = 0
    for w in spec["words"]:
        got = vvx.plain_kana(w["surface"])
        want = w["pronunciation"]
        # VOICEVOX の kana 表記は長音を母音字で返す（こう→コオ, けい→ケエ）
        norm = (got.replace("オオ", "オウ").replace("エエ", "エイ")
                   .replace("コオ", "コウ").replace("ソオ", "ソウ"))
        ok = want in (got, norm) or _loose_eq(got, want)
        if not ok:
            print(f"   ✗ {w['surface']}: 期待 {want} / 実際 {got}")
            bad += 1
    if not bad:
        print(f"   ✓ 全{len(spec['words'])}語が期待どおり")
    return bad


def _loose_eq(got, want):
    """長音の表記差（オオ/オウ, エエ/エイ）を無視して比較"""
    def norm(s):
        s = s.replace("オウ", "オオ").replace("エイ", "エエ")
        s = s.replace("ュウ", "ュオ").replace("ョウ", "ョオ")
        return s
    return norm(got) == norm(want)


def check_durations(files):
    print("\n── 4. 尺 ──")
    rows = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        rows.append((f.name, d["stats"]["est_minutes"], d["stats"]["cuts"],
                     d["stats"]["student_lines"]))
    total = sum(r[1] for r in rows)
    out = [r for r in rows if not (MIN_MINUTES <= r[1] <= MAX_MINUTES)]
    print(f"   {len(rows)}本 / 合計 {total/60:.1f}時間 / 平均 {total/max(len(rows),1):.1f}分")
    if out:
        for name, m, c, s in out:
            print(f"   ⚠ {name}: {m}分（想定 {MIN_MINUTES}〜{MAX_MINUTES}分の外）")
    else:
        print(f"   ✓ 全本が {MIN_MINUTES}〜{MAX_MINUTES}分の範囲")
    return len(out)


def sweep_readings(levels, limit=None):
    """教科書キーワードの漢字熟語の読みを一覧化（新しい誤読を探すため）"""
    print("\n── 3. 難読語の掃き出し ──")
    known = {w["surface"] for w in
             json.loads(vvx.YOMI.read_text(encoding="utf-8"))["words"]}
    terms = collections.Counter()
    for lv in levels:
        for f in OUTLINE_DIR.glob(f"{lv}_ch*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            for s in d["sections"]:
                for b in s["blocks"]:
                    for t in b.get("terms", []) + b.get("terms_x", []):
                        terms[t] += 1
    cands = [t for t in terms
             if re.fullmatch(r"[一-龥]{2,6}", t) and t not in known]
    cands.sort(key=lambda x: -terms[x])
    if limit:
        cands = cands[:limit]
    out = HERE / "out" / "readings.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write("頻度\t表記\t読み\n")
        for t in cands:
            fh.write(f"{terms[t]}\t{t}\t{vvx.plain_kana(t)}\n")
    print(f"   {len(cands)}語の読みを {out} に出力（目視レビュー用）")
    print("   誤読を見つけたら dict/yomi.json に追記して 03 を再実行")



# ------------------------------------------------------------ 事実照合（02b の生成台本用）

def check_facts(script_path, outline_dir):
    """LLM が生成した講義台本に、素材に無い条文番号・数値が混ざっていないか調べる。

    02b_build_lecture.py はプロンプトで縛っているが、生成物は必ず機械で照合する。
    条文番号と数値は「素材にその数字が出てくるか」で見る。
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "b2", str(Path(__file__).parent / "02b_build_lecture.py"))
    b2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b2)

    sc = json.loads(Path(script_path).read_text(encoding="utf-8"))
    if sc.get("mode") != "lecture":
        return []
    m = re.match(r"(\w+)_ch(\d+)_s(\d+)(?:p(\d+))?", Path(script_path).stem)
    level, ch, sec = m.group(1), int(m.group(2)), int(m.group(3))
    part = int(m.group(4)) if m.group(4) else None
    _, _, blocks, _ = b2.load_part_blocks(level, ch, sec, part)
    material = "\n".join(b2.block_to_text(b) for b in blocks)

    spoken = " ".join(
        [c["speech"] for c in sc["cuts"]]
        + [b for c in sc["cuts"] for b in (c["display"].get("bullets") or [])])

    ng = []
    # 条文番号（○条／○条の○／○項）
    for art in sorted(set(re.findall(r"(\d+)条", spoken))):
        if f"{art}条" not in material:
            ng.append(("条文番号", f"{art}条"))
    # 単位付きの数値
    for num, unit in set(re.findall(
            r"(\d+(?:,\d{3})*)\s*(年|か月|日|%|パーセント|円|万円|億円|分の\d+)", spoken)):
        if num.replace(",", "") not in material.replace(",", ""):
            ng.append(("数値", f"{num}{unit}"))
    return ng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=["2kyu", "3kyu", "hr"], action="append")
    ap.add_argument("--check-readings", action="store_true",
                    help="キーワードの読みを全件掃き出す（時間がかかる）")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    levels = args.level or ["2kyu", "3kyu"]

    vvx.ensure_engine()
    print(f"VOICEVOX {json.dumps(vvx.version(), ensure_ascii=False)}\n")

    files = load_scripts(levels)
    if not files:
        print("台本がありません。02b_build_lecture.py を先に実行してください。")
        return

    _, sym_bad = check_symbols(files)
    yomi_bad = check_yomi_dict()
    dur_bad = check_durations(files)
    if args.check_readings:
        sweep_readings(levels, args.limit)

    print("\n" + "=" * 52)
    verdict = "✓ 合成に進めます" if (sym_bad == 0 and yomi_bad == 0) else "✗ 先に修正してください"
    print(f"{verdict}   記号NG {sym_bad} / 辞書NG {yomi_bad} / 尺の外れ {dur_bad}")


if __name__ == "__main__":
    main()
