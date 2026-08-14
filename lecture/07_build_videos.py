#!/usr/bin/env python3
"""
Step 7: 台本から動画までを一気に通す（04 → 05 → 06）

02b で台本を作った後、スライド描画・音声合成・結合をまとめて回す。
既に mp4 がある本はスキップするので、失敗した本だけ作り直せる。

音声合成（05）は VOICEVOX が1プロセスなので並列にしても速くならない。
描画（04）と結合（06）は CPU を使い切るため、本単位で直列に回すのが素直。

使い方:
  python3 07_build_videos.py --level 2kyu --chapter 1
  python3 07_build_videos.py --level 2kyu --chapter 1 --force
  python3 07_build_videos.py --level 2kyu            # 台本がある全部
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT_DIR = HERE / "out" / "script"
VIDEO_DIR = HERE / "out" / "video"


def run_stage(script, level, ch, sec, part, extra=None):
    cmd = [sys.executable, str(HERE / script), "--level", level,
           "--chapter", str(ch), "--section", str(sec)]
    if part:
        cmd += ["--part", str(part)]
    cmd += extra or []
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{script} 失敗: {(r.stderr or r.stdout)[-400:]}")
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="2kyu")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    pat = f"{a.level}_ch{a.chapter:02d}_s*.json" if a.chapter else f"{a.level}_ch*_s*.json"
    targets = []
    for p in sorted(SCRIPT_DIR.glob(pat)):
        m = re.match(rf"{a.level}_ch(\d+)_s(\d+)(?:p(\d+))?\.json", p.name)
        if not m:
            continue
        ch, sec = int(m.group(1)), int(m.group(2))
        part = int(m.group(3)) if m.group(3) else None
        mp4 = VIDEO_DIR / f"{p.stem}.mp4"
        if mp4.exists() and not a.force:
            print(f"  – {p.stem} は既にあるのでスキップ")
            continue
        targets.append((ch, sec, part, p))

    if not targets:
        print("作る対象がありません")
        return

    print(f"対象 {len(targets)} 本\n")
    ok, ng = [], []
    t0 = time.time()
    for i, (ch, sec, part, sp) in enumerate(targets, 1):
        st = json.loads(sp.read_text(encoding="utf-8"))["stats"]
        head = f"[{i}/{len(targets)}] {sp.stem}  {st['cuts']}カット/{st['est_minutes']}分"
        print(head)
        s = time.time()
        try:
            for stage, label in (("04_render_slides.py", "スライド"),
                                 ("05_tts.py", "音声"),
                                 ("06_compose_video.py", "結合")):
                m = time.time()
                run_stage(stage, a.level, ch, sec, part)
                print(f"      {label:<6}{time.time()-m:>6.0f}秒")
            ok.append(sp.stem)
            print(f"      ✓ 完了 {time.time()-s:>6.0f}秒\n")
        except Exception as e:
            ng.append((sp.stem, str(e)[:200]))
            print(f"      ✗ {str(e)[:200]}\n")

    print(f"完了 {len(ok)} / 失敗 {len(ng)} / 所要 {(time.time()-t0)/60:.1f}分")
    for n, e in ng:
        print(f"  ✗ {n}: {e}")
    if ng:
        sys.exit(1)


if __name__ == "__main__":
    main()
