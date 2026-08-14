"""章の全動画を1本に結合する。SRT も時刻をずらして統合する。

  python3 08_concat.py --level hr --chapter 1

同じ設定で書き出した mp4 同士なので再エンコードせずに連結できる（-c copy）。
節ごとに見るより通しで見たい場合はこちら。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
VIDEO_DIR = HERE / "out" / "video"

TS = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d)")


def parse_ts(m) -> float:
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000


def fmt_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h, r = divmod(t, 3600)
    mi, s = divmod(r, 60)
    return f"{int(h):02d}:{int(mi):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def shift_srt(text: str, offset: float, start_index: int) -> tuple[str, int]:
    """SRT のタイムコードを offset 秒ずらし、通し番号を振り直す。"""
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    out, idx = [], start_index
    for b in blocks:
        lines = b.splitlines()
        # 1行目が通し番号、2行目が時刻
        if len(lines) < 2:
            continue
        time_line = lines[1]

        def rep(m):
            return fmt_ts(parse_ts(m) + offset)

        lines[0] = str(idx)
        lines[1] = TS.sub(rep, time_line)
        out.append("\n".join(lines))
        idx += 1
    return "\n\n".join(out), idx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--out", default=None, help="出力ファイル名")
    args = ap.parse_args()

    prefix = f"{args.level}_ch{args.chapter:02d}_s"
    parts = sorted(p for p in VIDEO_DIR.glob(f"{prefix}*.mp4")
                   if re.fullmatch(rf"{re.escape(prefix)}\d+", p.stem))
    if not parts:
        sys.exit(f"結合対象がありません: {VIDEO_DIR}/{prefix}*.mp4")

    out_mp4 = Path(args.out) if args.out else \
        VIDEO_DIR / f"{args.level}_ch{args.chapter:02d}_full.mp4"
    out_srt = out_mp4.with_suffix(".srt")

    print(f"{len(parts)}本を結合します")
    for p in parts:
        print(f"  {p.name}  {duration(p)/60:.1f}分")

    # 同じ設定で書き出しているので再エンコード不要
    listfile = VIDEO_DIR / f"_concat_{args.level}_ch{args.chapter:02d}.txt"
    listfile.write_text(
        "".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listfile), "-c", "copy", "-movflags", "+faststart",
         str(out_mp4)], check=True)
    listfile.unlink()

    # SRT を積み上げる。offset は「実際の mp4 の長さ」の累積を使う
    # （台本の想定尺ではなく実測値でないと、後半ほどずれる）
    merged, idx, offset = [], 1, 0.0
    for p in parts:
        srt = p.with_suffix(".srt")
        if srt.exists():
            text, idx = shift_srt(srt.read_text(encoding="utf-8"), offset, idx)
            merged.append(text)
        offset += duration(p)
    out_srt.write_text("\n\n".join(merged) + "\n", encoding="utf-8")

    total = duration(out_mp4)
    print(f"\n→ {out_mp4}  {total/60:.1f}分 "
          f"{out_mp4.stat().st_size/1e6:.1f}MB")
    print(f"→ {out_srt}  {idx-1}字幕")


if __name__ == "__main__":
    main()
