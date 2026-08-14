#!/usr/bin/env python3
"""
Step 5: 台本JSON → カットごとの音声（VOICEVOX）

講師 = 春日部つむぎ(8) / 生徒 = 中部つるぎ(94、驚きは おどおど 97)。
起動時に dict/yomi.json をエンジンのユーザー辞書へ反映するので、
褥瘡・嚥下・近居などの誤読は自動で直る。

ローカル実行なので何度作り直しても無料。原稿を直したら --resume を外して回せばよい。

使い方:
  python3 05_tts.py --level 2kyu --chapter 1 --section 1
  python3 05_tts.py --level 2kyu --chapter 1 --section 1 --limit 20
  python3 05_tts.py --level 2kyu --chapter 1 --section 1 --resume   # 既存はスキップ
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import vvx

HERE = Path(__file__).parent
SCRIPT_DIR = HERE / "out" / "script"
AUDIO_DIR = HERE / "out" / "audio"

SPEED = 1.05          # 教材なので少しだけ速める（実測 約380字/分）
STUDENT_SPEED = 1.02  # 生徒はもう一段ゆっくりにして聞き分けやすくする

# 条文の項番号。VOICEVOX は「501条①」を「ゴヒャクイチジョオ イチノ」と読み、
# 「1項」の意味が消えてしまう（audio_query の kana で確認済み）。
# ダッシュ・かぎ括弧・中黒は読み飛ばすか句点として扱われるので手を入れない。
MARU = {"①": "1項", "②": "2項", "③": "3項", "④": "4項", "⑤": "5項",
        "⑥": "6項", "⑦": "7項", "⑧": "8項", "⑨": "9項", "⑩": "10項"}


def normalize_for_speech(text):
    """読み上げ前に、辞書では直せない記号を言葉に置き換える。

    字幕は台本の subtitle から作るので、画面には元の「①」が残る。
    """
    for k, v in MARU.items():
        text = text.replace(k, v)
    return text


def wav_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--section", type=int, required=True)
    ap.add_argument("--part", type=int, help="前編/後編に分割された節のパート番号（1,2,…）")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    key = f"{args.level}_ch{args.chapter:02d}_s{args.section:02d}"
    if getattr(args, "part", None):
        key += f"p{args.part}"
    sp = SCRIPT_DIR / f"{key}.json"
    if not sp.exists():
        sys.exit(f"台本がありません: {sp}")
    meta = json.loads(sp.read_text(encoding="utf-8"))

    started = vvx.ensure_engine()
    added, updated = vvx.apply_yomi_dict()
    print(f"VOICEVOX {vvx.version()}"
          f"{'（起動しました）' if started else '（すでに起動中）'}"
          f" / 読み辞書 新規{added} 更新{updated}\n")

    out = AUDIO_DIR / key
    out.mkdir(parents=True, exist_ok=True)

    cuts = meta["cuts"][: args.limit] if args.limit else meta["cuts"]
    timings = []
    t0 = time.time()
    total_audio = 0.0

    for i, cut in enumerate(cuts, 1):
        wav = out / f"cut{cut['no']:03d}.wav"
        speaker = vvx.speaker_for(cut["speaker"], cut.get("style"))
        speed = STUDENT_SPEED if cut["speaker"] == "student" else SPEED
        if not (args.resume and wav.exists()):
            vvx.synth(normalize_for_speech(cut["speech"]), speaker, wav, speed=speed)
        d = wav_duration(wav)
        total_audio += d
        timings.append({"no": cut["no"], "kind": cut["kind"],
                        "speaker": cut["speaker"], "style": cut.get("style"),
                        "speaker_id": speaker, "wav": wav.name,
                        "duration": round(d, 3),
                        "subtitle": cut["subtitle"]})
        if i % 10 == 0 or i == len(cuts):
            el = time.time() - t0
            print(f"  [{i}/{len(cuts)}] 音声 {total_audio/60:.1f}分 / "
                  f"経過 {el:.0f}秒 (実時間比 {total_audio/max(el,0.01):.1f}x)")

    (out / "timings.json").write_text(
        json.dumps({"key": key, "speed": SPEED,
                    "total_seconds": round(total_audio, 2),
                    "cuts": timings}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(f"\n{len(cuts)} カット / 音声 {total_audio/60:.1f}分 → {out}")
    print(f"話速 {SPEED} で実測 "
          f"{sum(len(c['speech']) for c in cuts)/max(total_audio,0.01)*60:.0f}字/分")


if __name__ == "__main__":
    main()
