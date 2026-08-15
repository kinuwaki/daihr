"""SRT を、ウェブ再生に適した WebVTT に変換する。

  python3 09_make_vtt.py --level hr --chapter 1 --out ../docs/hr_ch01_full.vtt

## なぜ単純変換では駄目か

台本の1カット＝1字幕でSRTを作っているので、1件が平均85字・3行になる。
これをそのまま字幕として出すと画面下部の三分の一を覆い、
スライドの内容に重なって読めなくなる。

ここでは1カットの字幕を**句点で分割**し、表示時間を字数比で割り振る。
1件あたり2行・最大40字程度に収める（放送字幕の慣例に合わせた）。
"""

import argparse
import re
from pathlib import Path

HERE = Path(__file__).parent
VIDEO_DIR = HERE / "out" / "video"

MAX_CHARS = 40      # 1件あたりの上限。超えるとさらに分割する
MAX_LINE = 20       # 1行あたりの字数。2行に折り返す
MIN_DUR = 1.2       # 1件の最短表示秒数

TS = re.compile(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)")


def parse_ts(s: str) -> float:
    m = TS.search(s)
    h, mi, sec, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(sec) + int(ms) / 1000


def fmt_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h, r = divmod(t, 3600)
    mi, s = divmod(r, 60)
    return f"{int(h):02d}:{int(mi):02d}:{s:06.3f}"


def split_text(text: str) -> list[str]:
    """句点で切り、それでも長ければ読点で切る。"""
    # 元のSRTは折り返し済みなので、まず改行を取り除いて1本の文にする
    text = text.replace("\n", "")

    # 句点のうしろで切る（句点は残す）
    parts = [p for p in re.split(r"(?<=。)", text) if p]

    out = []
    for p in parts:
        if len(p) <= MAX_CHARS:
            out.append(p)
            continue
        # 長すぎる場合は読点で切る
        subs = [s for s in re.split(r"(?<=、)", p) if s]
        buf = ""
        for s in subs:
            if buf and len(buf) + len(s) > MAX_CHARS:
                out.append(buf)
                buf = s
            else:
                buf += s
        if buf:
            out.append(buf)
    return out or [text]


def wrap(text: str) -> str:
    """2行に折り返す。字幕は3行以上にしない。"""
    if len(text) <= MAX_LINE:
        return text
    mid = len(text) // 2
    # 中央にいちばん近い読点で折る。無ければ中央で折る
    cand = [m.end() for m in re.finditer("、", text)]
    cut = min(cand, key=lambda c: abs(c - mid)) if cand else mid
    return text[:cut] + "\n" + text[cut:]


def convert(srt_path: Path) -> str:
    src = srt_path.read_text(encoding="utf-8")
    blocks = [b for b in re.split(r"\n\s*\n", src.strip()) if b.strip()]

    cues = []
    for b in blocks:
        lines = b.splitlines()
        if len(lines) < 3:
            continue
        start, end = (parse_ts(x) for x in lines[1].split(" --> "))
        body = "".join(lines[2:])

        pieces = split_text(body)
        total = sum(len(p) for p in pieces) or 1
        # 表示時間を字数比で割り振る。読む速さは字数に比例するため
        t = start
        span = end - start
        for p in pieces:
            d = max(MIN_DUR, span * len(p) / total)
            # 元の区間を超えない
            e = min(end, t + d)
            if e - t < 0.2:          # 端数で潰れた分は捨てる
                continue
            cues.append((t, e, wrap(p)))
            t = e

    out = ["WEBVTT", ""]
    for i, (s, e, txt) in enumerate(cues, 1):
        out.append(str(i))
        out.append(f"{fmt_ts(s)} --> {fmt_ts(e)}")
        out.append(txt)
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    srt = VIDEO_DIR / f"{args.level}_ch{args.chapter:02d}_full.srt"
    if not srt.exists():
        raise SystemExit(f"SRTがありません: {srt}")

    vtt = convert(srt)
    Path(args.out).write_text(vtt, encoding="utf-8")

    n = vtt.count("-->")
    lens = [len(l) for blk in vtt.split("\n\n")[1:]
            for l in blk.splitlines()[2:] if l]
    print(f"{srt.name} → {args.out}")
    print(f"  字幕 {n}件 / 1行あたり平均 {sum(lens)/len(lens):.0f}字 "
          f"/ 最長 {max(lens)}字")


if __name__ == "__main__":
    main()
