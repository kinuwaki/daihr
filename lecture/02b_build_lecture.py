#!/usr/bin/env python3
"""
Step 2b: 構造JSON → 授業プレゼンの台本JSON（LLMで講義原稿に書き換える）

設計:
  画面は「要約」（体言止めの短い要点）、音声は「話し言葉」（講師の語り）。
  教科書をそのまま読み上げるのはプレゼンではないので、両方を LLM に書かせる。
  以前あった全文逐読版（02_build_script.py）は朗読になってしまうため廃止した。

生成は claude CLI の非対話モード（claude -p）で行う。
APIキーの設定は不要で、標準出力に JSON がそのまま返る。

事実の管理:
  - 素材（教科書）に無い法令名・条文番号・数値を使わないようプロンプトで縛る
  - 生成後に 03_review_script.py --check-facts で素材と機械照合する
  - 逸脱が見つかったカットは差し戻して再生成する

使い方:
  python3 02b_build_lecture.py --level 2kyu --chapter 1 --section 1 --part 1
  python3 02b_build_lecture.py --level 2kyu --chapter 1              # ch1 の全パート
  python3 02b_build_lecture.py --level 2kyu --chapter 1 --jobs 4     # 4並列
  python3 02b_build_lecture.py --level 2kyu --chapter 1 --section 1 --dry-run
"""
import argparse
import json
import re
import pathlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUTLINE_DIR = HERE / "out" / "outline"
SCRIPT_DIR = HERE / "out" / "script"
LECTURE_DIR = HERE / "out" / "lecture"

CREDITS = ["VOICEVOX:春日部つむぎ"]
CHARS_PER_MIN = 360

PROMPT = """JSON だけを出力してください。前置き・説明・コードフェンスは一切不要です。
ファイルの読み書きや検索は不要です。渡された素材だけを使ってください。

# 依頼

社内異動支援AIの作り方を解説した技術記事の一部を素材として渡します。
これを「講師が授業で解説するプレゼン」の台本に書き換えてください。

重要な前提として、**スライドの文字と講師のしゃべりは別物**です。

- スライド … 要約。体言止めの短い要点。読み上げ文をそのまま載せない
- しゃべり … 話し言葉。「〜ですね」「〜でしょうか」「ここ、大事です」のような口調

教科書の文をそのまま読み上げるのは禁止です。必ず口語に開いてください。

# カットの種類を使い分けてください（最重要）

同じ形のスライドが続くと、見ている人はすぐ飽きます。
素材のブロックには [B0] [B1] … と番号が振ってあります。
**条文・表・図・まちがえやすい点・事例は、その番号を指定してください。**
スライドは教科書の実物から描くので、あなたが中身を作る必要はありません。
あなたが書くのは、そのブロックを見せながら話す**しゃべりだけ**です。

使える種類:

| type | いつ使うか | あなたが書くもの |
|---|---|---|
| `talk` | 本文（[Bn] が本文のもの）をまとめて解説するとき | 見出し＋要点＋要点ごとのしゃべり |
| `question` | 論点に入る前に問いを投げるとき | 問い1行＋しゃべり |
| `law` | 条文のブロックを見せるとき | ブロック番号＋しゃべり |
| `pitfall` | まちがえやすい点のブロックを見せるとき | ブロック番号＋しゃべり |
| `case` | 事例のブロックを見せるとき | ブロック番号＋しゃべり |
| `table` | 表のブロックを見せるとき | ブロック番号＋しゃべり |
| `figure` | 図のブロックを見せるとき | ブロック番号＋しゃべり |
| `number` | 数値や条文番号を強く印象づけたいとき | 数値＋そえ書き＋しゃべり |

**素材に条文・表・図・まちがえやすい点・事例のブロックがあれば、必ずその種類で出してください。**
本文と同じ扱いにして talk に混ぜてはいけません。
`question` は論点の入口に、`number` は覚えてほしい数字に使ってください。

# talk の中では、しゃべりと要点を1対1で対応させる

**要点1つにつき、しゃべり1本。**そのしゃべりは、その要点だけを説明するものにしてください。
動画では、しゃべっている間その要点がハイライトされます。
「いま声で言っていること」と「いま光っている要点」が食い違うと、見ている人が混乱します。

# 授業として入れてほしい要素

- 論点の前に問いを立て、少し置いてから答える（`question` を使う）
- 数字・条文番号は「ここは覚えてください」と明示して強調する（`number` を使う）
- まちがえやすい点は「引っかかるのはここです」と対比で示す
- 前に説明したことと結びつける（「さきほどの〜を思い出してください」）
{edge}

# 絶対に守ること（事実の管理）

- **法令名・条文番号・数値・制度名は、素材に書かれているものだけを使う。**
  素材に無い条文番号を作ってはいけません。うろ覚えの知識を足さないこと。
- 素材にない結論・例外・判例を追加しないこと。素材の範囲内で語ること。
- 固有名詞（人名・会社名）は素材の事例に出てくるものだけ使うこと。
- 言い換えは自由ですが、**法的な意味を変えてはいけません**。
  「推定する」を「みなす」に変えるような書き換えは誤りです。

# 出力する JSON の形

{{
  "cuts": [
    {{"type": "question", "text": "問い（15〜30字）", "speech": "しゃべり"}},
    {{"type": "talk", "head": "見出し（10〜20字）",
      "bullets": [{{"text": "要点（15〜30字・体言止め）", "speech": "この要点だけを説明するしゃべり"}}]}},
    {{"type": "law", "block": 3, "speech": "条文を見せながらのしゃべり"}},
    {{"type": "number", "value": "20年", "label": "特許権の存続期間", "speech": "しゃべり"}},
    {{"type": "pitfall", "block": 5, "speech": "しゃべり"}},
    {{"type": "table", "block": 7, "speech": "しゃべり"}},
    {{"type": "case", "block": 9, "speech": "しゃべり"}},
    {{"type": "figure", "block": 1, "speech": "しゃべり"}}
  ]
}}

- cuts は素材の流れの順に並べてください
- speech は1本 **{per_bullet}字前後**（約18秒）
- talk の bullets は1枚に3〜5個
- talk の枚数は **{n_slides}枚**、要点は全部で **{n_bullets}個** を目安に

# 素材（第{ch}章「{ch_title}」第{sec}節「{sec_title}」{part_label}）

{material}
"""


def block_to_text(b, idx=None):
    """素材ブロックを、LLMに渡す読みやすい形にする。

    idx を渡すと [B0] のような番号を付ける。
    条文・表・図・まちがえやすい点・事例は、スライドを教科書の実物から描くので、
    LLM には「この番号のブロックを出す」と指示させ、中身は作らせない。
    """
    t = b["type"]
    tag = f"[B{idx}] " if idx is not None else ""
    if t == "h3":
        return f"\n## {tag}{b['text']}\n"
    if t == "p":
        return tag + b["text"]
    if t == "law":
        # 01 の出力キーは articles（[{label, text}]）。items ではない
        body = "\n".join(f"  - {a.get('label','')}：{a.get('text','')}"
                         for a in (b.get("articles") or []))
        return f"【条文 {tag}】\n{body}"
    if t == "pitfall":
        return f"【まちがえやすい点 {tag}】" + " ".join(b.get("paras") or [])
    if t == "case":
        return f"【事例 {tag}】" + " ".join(b.get("paras") or [])
    if t == "point":
        return f"【まとめ {tag}】" + " ".join(b.get("paras") or [])
    if t == "table":
        head = " / ".join(b.get("head") or [])
        rows = "\n".join("  - " + " / ".join(r) for r in (b.get("rows") or []))
        return f"【表 {tag}】{head}\n{rows}"
    if t == "figure":
        return f"【図 {tag}】{b.get('ftitle','')} {b.get('caption','')}"
    return ""


# 尺の見積もりと、プロンプトに渡す分量の指示は別の係数を使う。
#
# SPEECH_PER_SRC : 実際のしゃべり字数 ÷ 素材字数。**表示と分割判定**に使う。
#   カット種別を増やして問い・条文・数値・表を挟むようになった結果、
#   素材の約1.9倍のしゃべりが出る（実測: 素材5,011字 → しゃべり9,526字）。
# BUDGET_PER_SRC : プロンプトに「要点N個」と伝えるための係数。
#   こちらを大きくすると出力がさらに膨らむので、実測と揃えずに据え置く。
SPEECH_PER_SRC = 1.90
BUDGET_PER_SRC = 0.81   # = 0.60 × 1.35（旧 LEC_RATIO × READ_INFLATE）
MAX_MINUTES = 30        # 長いこと自体は問題にしない方針。
                        # 分けたいときはこの値を下げて作り直す


def _src_chars(blocks):
    return sum(len(b.get("text", "")) + sum(len(x) for x in b.get("paras", []))
               for b in blocks)


def est_minutes(blocks):
    """実際に出てくる尺の見積もり（表示・分割判定用）"""
    return _src_chars(blocks) * SPEECH_PER_SRC / CHARS_PER_MIN


def split_blocks(blocks, max_minutes=MAX_MINUTES):
    """h3 の境界だけで分割し、[(ブロック列, ラベル), ...] を返す。
    文やボックスの途中では割らない。"""
    total = est_minutes(blocks)
    if total <= max_minutes:
        return [(blocks, "")]

    groups, cur = [], []
    for b in blocks:
        if b["type"] == "h3" and cur:
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)

    n = -(-int(total * 100) // int(max_minutes * 100)) or 1
    target = total / n
    parts, cur, cur_m = [], [], 0.0
    for g in groups:
        gm = est_minutes(g)
        if cur and cur_m + gm > target * 1.15 and len(parts) < n - 1:
            parts.append(cur)
            cur, cur_m = [], 0.0
        cur.extend(g)
        cur_m += gm
    if cur:
        parts.append(cur)

    labels = ["前編", "後編", "第3部", "第4部", "第5部"]
    return [(pt, f"（{labels[i] if i < len(labels) else f'第{i+1}部'}）")
            for i, pt in enumerate(parts)]


def load_part_blocks(level, ch_num, sec_num, part):
    """素材から直接パートを切り出す"""
    path = OUTLINE_DIR / f"{level}_ch{ch_num:02d}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ch = data["chapter"]
    sec = next((s for s in data["sections"] if s["num"] == sec_num), None)
    if sec is None:
        sys.exit(f"節が見つかりません: ch{ch_num} s{sec_num}")

    parts = split_blocks(sec["blocks"])
    if part is None:
        if len(parts) > 1:
            sys.exit(f"ch{ch_num} s{sec_num} は {len(parts)} 分割されます。--part を指定してください")
        return ch, sec, parts[0][0], parts[0][1]
    if not 1 <= part <= len(parts):
        sys.exit(f"ch{ch_num} s{sec_num} のパートは 1〜{len(parts)} です")
    return ch, sec, parts[part - 1][0], parts[part - 1][1]


PER_BULLET = 110        # 1要点あたりのしゃべり字数。110字 ≒ 18秒
BULLETS_PER_SLIDE = 4
BATCH_SRC_CHARS = 1800  # 1回の生成に渡す素材の上限。
                        # まとめて投げると応答が出力上限で切れたので、
                        # h3 グループ単位に分けて安全な大きさで回す。

FIRST_HINT = "- このかたまりは節の入口です。1枚目で素朴な疑問を投げてください（「そもそも、なぜ〜なんでしょうか」）"
LAST_HINT = "- このかたまりは節の締めです。最後のスライドで、扱った論点を一息で振り返ってください"


def batch_blocks(blocks, limit=BATCH_SRC_CHARS):
    """h3 の境界で、素材が limit 字を超えないかたまりに分ける"""
    groups, cur = [], []
    for b in blocks:
        if b["type"] == "h3" and cur:
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)

    batches, cur, n = [], [], 0
    for g in groups:
        gn = _src_chars(g)
        if cur and n + gn > limit:
            batches.append(cur)
            cur, n = [], 0
        cur.extend(g)
        n += gn
    if cur:
        batches.append(cur)
    return batches


def build_prompt(ch, sec, blocks, label, is_first=True, is_last=True):
    """尺は「字数の目安」ではなく「要点の個数」で縛る。
    字数だけ伝えても超過したので、個数に落として指示する。"""
    material = "\n\n".join(
        x for x in (block_to_text(b, i) for i, b in enumerate(blocks)) if x.strip())
    # 分量の指示は素材の量から出す。est_minutes（実測ベース）を使うと
    # 「長く出る → もっと長く指示する」の悪循環になるので分けている。
    target = int(_src_chars(blocks) * BUDGET_PER_SRC)
    n_bullets = max(3, round(target / PER_BULLET))
    n_slides = max(1, round(n_bullets / BULLETS_PER_SLIDE))
    edge = "\n".join(x for x in (FIRST_HINT if is_first else "",
                                 LAST_HINT if is_last else "") if x)
    return PROMPT.format(ch=ch["num"], ch_title=ch["title"],
                         sec=sec["num"], sec_title=sec["title"], part_label=label,
                         material=material, n_slides=n_slides,
                         n_bullets=n_bullets, per_bullet=PER_BULLET, edge=edge), target


def strip_fence(text):
    """コードフェンスを剥がして JSON 本体だけを取り出す"""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    i = t.find("{")
    if i < 0:
        raise ValueError(f"JSON が見つからない: {text[:200]}")
    return t[i:]


def repair_json(t):
    """閉じ括弧が足りない JSON を、完成している分だけ残して閉じる。

    stop_reason が end_turn でも、末尾の ]} が抜けた応答がしばしば返る。
    括弧を補うだけなので、内容を作り足すことはしない。
    文字列の途中で終わっている場合は、直前の完成したオブジェクトまで戻す。
    """
    stack, inside, esc, last_safe = [], False, False, None
    for k, c in enumerate(t):
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            inside = not inside
            continue
        if inside:
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]":
            if stack:
                stack.pop()
            if len(stack) >= 2:
                last_safe = k + 1          # 要素が1つ閉じ切れた位置
    body = t
    if inside and last_safe:
        body = t[:last_safe]               # 文字列途中で切れていたら戻す
        stack, inside, esc = [], False, False
        for c in body:
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"':
                inside = not inside
                continue
            if inside:
                continue
            if c in "{[":
                stack.append(c)
            elif c in "}]" and stack:
                stack.pop()
    closers = "".join("}" if o == "{" else "]" for o in reversed(stack))
    return body + closers



def call_claude(prompt, model=None, timeout=1800, tag="", retries=2):
    """claude -p を叩いて slides を取り出す。

    --output-format json で封筒ごと受け取り、stop_reason を見て
    出力上限による切断を検出する。切れていたら短く作り直させる。
    """
    for attempt in range(retries + 1):
        pr = prompt if attempt == 0 else prompt + (
            "\n\n# 追加指示\n前回の応答が長すぎて途中で切れました。"
            "要点の個数を2割減らし、speech も短くして、必ず JSON を閉じてください。")
        cmd = ["claude", "-p", pr, "--output-format", "json"]
        if model:
            cmd += ["--model", model]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"claude が失敗 {tag}: {(r.stderr or r.stdout)[-300:]}")
        env = json.loads(r.stdout)
        if env.get("is_error"):
            raise RuntimeError(f"claude がエラー {tag}: {str(env.get('result'))[:200]}")
        stop = env.get("stop_reason")
        body = strip_fence(env.get("result") or "")
        try:
            gen = json.loads(body)
            return gen.get("cuts") or []
        except json.JSONDecodeError:
            # 閉じ括弧が足りないだけなら補って救う
            try:
                gen = json.loads(repair_json(body))
                got = gen.get("cuts") or []
                if got:
                    print(f"  … JSON を修復して {len(got)}カットを回収 {tag}")
                    return got
            except Exception:
                pass
        try:
            gen = json.loads(body)
            return gen.get("cuts") or []
        except Exception as e:
            if attempt >= retries:
                raise RuntimeError(
                    f"JSON を解析できない {tag}（stop_reason={stop}）: {e}")
            print(f"  … 再試行 {tag}（stop_reason={stop}）")


def to_cuts(gen, ch, sec, label, blocks):
    """LLM の出力を 04/05/06 が読めるカット列に変換する。

    条文・表・図・まちがえやすい点・事例は、LLM が指定したブロック番号をもとに
    **教科書の実物から** display を組む。LLM が書くのは speech だけなので、
    条文の文言や表の中身が生成物で書き換わることがない。
    """
    cuts = []

    def add(kind, speech, display, heading=""):
        speech = (speech or "").strip()
        if not speech:
            return
        cuts.append({"no": len(cuts) + 1, "kind": kind, "speaker": "teacher",
                     "style": None, "speech": speech, "subtitle": speech,
                     "heading": heading or display.get("head", ""), "display": display})

    def blk(c):
        """LLM が指定したブロックを取り出す。番号が変なら None"""
        try:
            b = blocks[int(c.get("block"))]
        except (TypeError, ValueError, IndexError):
            return None
        return b

    add("title", f"第{ch['num']}章、{ch['title']}。第{sec['num']}節、{sec['title']}{label}。",
        {"chapter": f"第{ch['num']}章 {ch['title']}", "chapter_sub": ch["sub"],
         "section": f"第{sec['num']}節", "title": sec["title"] + label,
         "credits": CREDITS})

    heading = ""
    for c in gen.get("cuts", []):
        t = (c.get("type") or "talk").lower()

        if t == "talk":
            heading = c.get("head", "") or heading
            bullets = [str(b.get("text", "")) for b in (c.get("bullets") or [])]
            # 要点1つ = 1カット。focus はその要点の位置なので対応がずれない
            for k, b in enumerate(c.get("bullets") or []):
                add("talk", b.get("speech", ""),
                    {"head": c.get("head", ""), "bullets": bullets, "focus": k})
            continue

        if t == "question":
            add("question", c.get("speech", ""),
                {"text": c.get("text", "")}, heading)
            continue

        if t == "number":
            add("number", c.get("speech", ""),
                {"value": c.get("value", ""), "label": c.get("label", "")}, heading)
            continue

        b = blk(c)
        if b is None:
            # ブロック番号が取れなければ、しゃべりだけは捨てずに見出しスライドで出す
            add("heading", c.get("speech", ""), {"title": heading or sec["title"]}, heading)
            continue

        if t == "law" and b["type"] == "law":
            items = [{"label": a.get("label", ""), "text": a.get("text", "")}
                     for a in (b.get("articles") or [])]
            add("law", c.get("speech", ""),
                {"title": strip_emoji(b.get("heading")) or "条文を見てみましょう",
                 "items": items, "focus": len(items) - 1}, heading)
        elif t == "pitfall" and b["type"] == "pitfall":
            add("pitfall", c.get("speech", ""),
                {"title": strip_emoji(b.get("heading")) or "まちがえやすいポイント",
                 "text": " ".join(b.get("paras") or []),
                 "wrong": b.get("terms_x") or [], "right": b.get("terms") or []}, heading)
        elif t == "case" and b["type"] == "case":
            add("case", c.get("speech", ""),
                {"title": strip_emoji(b.get("heading")) or "ケースで考えましょう",
                 "text": " ".join(b.get("paras") or [])}, heading)
        elif t == "table" and b["type"] == "table":
            add("table", c.get("speech", ""),
                {"head": b.get("head") or [], "rows": b.get("rows") or []}, heading)
        elif t == "figure" and b["type"] == "figure":
            add("figure", c.get("speech", ""),
                {"src": b.get("src", ""), "ftitle": b.get("ftitle", ""),
                 "caption": b.get("caption", "")}, heading)
        else:
            # 型とブロックの種類が食い違ったら talk として拾う
            add("heading", c.get("speech", ""), {"title": heading or sec["title"]}, heading)

    add("outro", "この節はここまでです。実装の詳細はリポジトリのコードを見てください。",
        {"title": "おつかれさまでした", "app": "github.com/kinuwaki/kikuhr",
         "credits": CREDITS})
    return cuts


def strip_emoji(h):
    return re.sub(r"^[^\wぁ-んァ-ヶ一-龥]+", "", h or "").strip()


def generate(level, ch_num, sec_num, part, dry=False, timeout=1800, model=None):
    ch, sec, blocks, label = load_part_blocks(level, ch_num, sec_num, part)
    key = f"{level}_ch{ch_num:02d}_s{sec_num:02d}" + (f"p{part}" if part else "")
    LECTURE_DIR.mkdir(parents=True, exist_ok=True)
    raw = LECTURE_DIR / f"{key}.raw.json"
    prompt, target = build_prompt(ch, sec, blocks, label)

    if dry:
        print(prompt)
        print(f"\n（目標 {target}字 / 素材 {len(blocks)}ブロック）")
        return None

    batches = batch_blocks(blocks)
    got, target, base = [], 0, 0
    for bi, bl in enumerate(batches):
        pr, tg = build_prompt(ch, sec, bl, label,
                              is_first=(bi == 0), is_last=(bi == len(batches) - 1))
        target += tg
        part_cuts = call_claude(pr, model=model, timeout=timeout,
                               tag=f"{key} [{bi+1}/{len(batches)}]")
        # バッチごとに [B0] から振り直しているので、全体の添字に直す
        for c in part_cuts:
            if isinstance(c.get("block"), int):
                c["block"] += base
        got += part_cuts
        base += len(bl)
    gen = {"cuts": got}
    raw.write_text(json.dumps(gen, ensure_ascii=False, indent=1), encoding="utf-8")
    cuts = to_cuts(gen, ch, sec, label, blocks)
    chars = sum(len(c["speech"]) for c in cuts)
    out = {
        "level": level, "chapter": ch["num"], "chapter_title": ch["title"],
        "chapter_sub": ch["sub"], "section": sec["num"],
        "section_title": sec["title"] + label,
        "img_base": str(pathlib.Path(__file__).parent.parent /
                        "textbook" / level / ch["dir"]) + "/",
        "credits": CREDITS, "mode": "lecture",
        "stats": {"cuts": len(cuts), "speech_chars": chars,
                  "est_minutes": round(chars / CHARS_PER_MIN, 1),
                  "target_chars": target, "student_lines": 0},
        "cuts": cuts,
    }
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (SCRIPT_DIR / f"{key}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{key}  カット{len(cuts):>3}  {chars:>5,}字（目標{target:,}）  "
          f"約{out['stats']['est_minutes']:>4.1f}分")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="2kyu")
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--section", type=int)
    ap.add_argument("--part", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--jobs", type=int, default=1, help="並列数")
    ap.add_argument("--model", help="claude --model に渡すモデル名")
    a = ap.parse_args()

    data = json.loads((OUTLINE_DIR / f"{a.level}_ch{a.chapter:02d}.json").read_text(encoding="utf-8"))
    if a.section:
        targets = [(a.section, a.part)]
    else:
        # 素材から、その章の（節, パート）一覧を組み立てる
        targets = []
        for sec in data["sections"]:
            parts = split_blocks(sec["blocks"])
            if len(parts) == 1:
                targets.append((sec["num"], None))
            else:
                targets += [(sec["num"], i + 1) for i in range(len(parts))]
    if a.dry_run or a.jobs <= 1:
        for sec_num, part in targets:
            generate(a.level, a.chapter, sec_num, part, dry=a.dry_run, model=a.model)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed
    ok = ng = 0
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(generate, a.level, a.chapter, s_, p_, False, 1800, a.model): (s_, p_)
                for s_, p_ in targets}
        for f in as_completed(futs):
            s_, p_ = futs[f]
            try:
                f.result()
                ok += 1
            except Exception as e:
                ng += 1
                print(f"  ✗ s{s_}{'p'+str(p_) if p_ else ''}: {str(e)[:180]}")
    print(f"\n成功 {ok} / 失敗 {ng}")
    if ng:
        sys.exit(1)


if __name__ == "__main__":
    main()
