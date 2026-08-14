#!/usr/bin/env python3
"""
Step 6: スライドPNG + 音声 → mp4（＋ SRT字幕）

各カットの表示時間は、そのカットの音声の長さで決まる。
話者が変わるところには少し間を入れる（対話のテンポ）。

字幕は台本の subtitle（記号を残した原文）から作るので、
読み上げ用に「12分の1」へ直した文ではなく「1/12」のまま出る。

使い方:
  python3 06_compose_video.py --level 2kyu --chapter 1 --section 1
  python3 06_compose_video.py --level 2kyu --chapter 1 --section 1 --limit 20 --suffix sample
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT_DIR = HERE / "out" / "script"
SLIDE_DIR = HERE / "out" / "slides"
AUDIO_DIR = HERE / "out" / "audio"
VIDEO_DIR = HERE / "out" / "video"

GAP_SAME = 0.16        # 同じ話者が続くときの間（秒）
GAP_SWITCH = 0.34      # 話者が変わるときの間
SR = 24000             # VOICEVOX の出力サンプリングレート

# 配信サイズの既定。s01（25分）で 46.8MB → 15.9MB（66%減）になった設定。
# スライドは静止画で、動くのはクロスフェード0.28秒だけなので 30fps は要らない。
# 720p でも条文カードの文字は読める（等倍で確認済み）。
# 音声は VOICEVOX のモノラル合成音声なので、ステレオ127kbps は過剰だった。
# 32k まで落とすと更に小さくなるが、音質を優先して 48k にしてある。
FPS = 15
W, H = 1280, 720
ABR = "48k"            # 音声ビットレート（mono）
ASR = 44100            # 音声サンプリングレート


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"失敗: {' '.join(map(str, cmd))[:200]}\n{r.stderr[-1200:]}")
    return r


def srt_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text, width=32):
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return "\n".join(lines[:3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--section", type=int, required=True)
    ap.add_argument("--part", type=int, help="前編/後編に分割された節のパート番号（1,2,…）")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--suffix", default="")
    ap.add_argument("--crf", type=int, default=28)
    ap.add_argument("--xfade", type=float, default=0.28,
                    help="カット間クロスフェードの秒数。0 で無効（既定0.28）")
    args = ap.parse_args()

    key = f"{args.level}_ch{args.chapter:02d}_s{args.section:02d}"
    if getattr(args, "part", None):
        key += f"p{args.part}"
    timings_path = AUDIO_DIR / key / "timings.json"
    if not timings_path.exists():
        sys.exit(f"音声がありません。05_tts.py を先に実行してください: {timings_path}")
    tm = json.loads(timings_path.read_text(encoding="utf-8"))
    cuts = tm["cuts"][: args.limit] if args.limit else tm["cuts"]

    slides = SLIDE_DIR / key
    audio = AUDIO_DIR / key
    missing = [c["no"] for c in cuts if not (slides / f"cut{c['no']:03d}.png").exists()]
    if missing:
        sys.exit(f"スライドPNGが足りません（{len(missing)}枚）。"
                 f"04_render_slides.py を実行してください: {missing[:12]}")

    work = VIDEO_DIR / key
    work.mkdir(parents=True, exist_ok=True)
    name = key + (f"_{args.suffix}" if args.suffix else "")

    # ── 間の無音を用意する ──
    for tag, sec in (("same", GAP_SAME), ("switch", GAP_SWITCH)):
        gap = work / f"_gap_{tag}.wav"
        if not gap.exists():
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                 "-i", f"anullsrc=r={SR}:cl=mono", "-t", str(sec), str(gap)])

    # ── 音声の連結リストと、画像の表示時間を同時に組む ──
    alist, ilist, subs, shown_list = [], [], [], []
    t = 0.0
    for i, c in enumerate(cuts):
        wav = audio / c["wav"]
        png = slides / f"cut{c['no']:03d}.png"
        nxt = cuts[i + 1] if i + 1 < len(cuts) else None
        gap = 0.0
        if nxt:
            gap = GAP_SWITCH if nxt["speaker"] != c["speaker"] else GAP_SAME
            gap_tag = "switch" if nxt["speaker"] != c["speaker"] else "same"

        alist.append(f"file '{wav.resolve()}'")
        if nxt:
            alist.append(f"file '{(work / f'_gap_{gap_tag}.wav').resolve()}'")

        shown = c["duration"] + gap
        shown_list.append((png, shown))
        ilist.append(f"file '{png.resolve()}'")
        ilist.append(f"duration {shown:.3f}")

        subs.append((t, t + c["duration"], c["subtitle"]))
        t += shown

    # concat デマクサは最後の画像をもう一度並べる必要がある
    ilist.append(f"file '{(slides / f'cut{cuts[-1]["no"]:03d}.png').resolve()}'")

    (work / "audio.txt").write_text("\n".join(alist) + "\n", encoding="utf-8")
    (work / "images.txt").write_text("\n".join(ilist) + "\n", encoding="utf-8")

    # ── 音声を1本に ──
    full_audio = work / "audio.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(work / "audio.txt"), "-c:a", "pcm_s16le", str(full_audio)])

    # ── 字幕 ──
    srt = VIDEO_DIR / f"{name}.srt"
    with srt.open("w", encoding="utf-8") as fh:
        for n, (a, b, text) in enumerate(subs, 1):
            fh.write(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{wrap(text)}\n\n")

    # ── 動画 ──
    # 静止画を並べるだけだと「紙芝居」になるので、カットの切り替わりを
    # クロスフェードでつなぐ。PNG を直接入力して xfade を数珠つなぎにする方式。
    #
    # ズーム（Ken Burns）は見送った。zoompan は静止画1枚13秒に対して
    # 実測 217秒（217倍）かかり、116本の規模では実用にならない。
    # 一方 xfade は51枚で約23秒で済む。チップの段階点灯が実質的な動きを
    # 担っているので、滑らかな遷移だけ足せば十分と判断した。
    mp4 = VIDEO_DIR / f"{name}.mp4"
    xf = max(0.0, args.xfade)

    if xf > 0 and len(shown_list) > 1:
        inputs = []
        for png, shown in shown_list:
            # xfade は前後が重なるので、重なる分だけ長めに用意する
            inputs += ["-loop", "1", "-t", f"{shown + xf:.3f}", "-i", str(png)]
        # xfade の offset は「連結後の時間軸での遷移開始位置」。
        # xfade 1回の出力長は offset + 後続入力の長さ になるので、
        #   L_i = (acc_i - xf) + (d_i + xf) = acc_i + d_i
        # となり、累積は素直に d の総和になる。
        # ここで xf を毎回引くと 1カットごとに xf ずつ前へずれ、
        # 72カットで約20秒の狂いになった（実測）。引くのは1回だけ。
        # PNG は 1920x1080 で描かれるので、xfade に入れる前に配信解像度へ落とす。
        # 先に縮めておくほうが xfade の処理量も減る。
        filt = [f"[{i}:v]scale={W}:{H}:flags=lanczos,setsar=1[s{i}]"
                for i in range(len(shown_list))]
        prev, acc = "s0", 0.0
        for i in range(1, len(shown_list)):
            acc += shown_list[i - 1][1]          # d_0 … d_{i-1} の総和
            filt.append(f"[{prev}][s{i}]xfade=transition=fade:"
                        f"duration={xf:.3f}:offset={max(0.0, acc - xf):.3f}[x{i}]")
            prev = f"x{i}"
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", str(full_audio),
             "-filter_complex", ";".join(filt),
             "-map", f"[{prev}]", "-map", f"{len(shown_list)}:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
             "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", ABR, "-ac", "1", "-ar", str(ASR),
             "-movflags", "+faststart", "-shortest", str(mp4)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-f", "concat", "-safe", "0", "-i", str(work / "images.txt"),
             "-i", str(full_audio),
             "-vf", f"scale={W}:{H}:flags=lanczos,setsar=1",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
             "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", ABR, "-ac", "1", "-ar", str(ASR),
             "-movflags", "+faststart", "-shortest", str(mp4)])

    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip())
    size = mp4.stat().st_size / 1024 / 1024

    print(f"✓ {mp4}")
    print(f"  {len(cuts)} カット / {dur/60:.1f}分 / {size:.1f}MB / 字幕 {srt.name}")


if __name__ == "__main__":
    main()
