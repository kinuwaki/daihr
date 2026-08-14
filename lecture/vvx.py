#!/usr/bin/env python3
"""
VOICEVOX エンジンの共通ラッパー（03 / 05 から使う）

エンジンは GUI を立ち上げずに同梱バイナリを直接起動できる。
  /Applications/VOICEVOX.app/Contents/Resources/vv-engine/run --host 127.0.0.1 --port 50021
"""

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
PORT = 50021
BASE = f"http://{HOST}:{PORT}"
ENGINE = Path("/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run")
YOMI = Path(__file__).parent / "dict" / "yomi.json"

# 話者
TEACHER_ID = 8       # 春日部つむぎ ノーマル（唯一の話者）
STUDENT_ID = 94      # 中部つるぎ ノーマル（生徒）
STUDENT_SURPRISE = 97  # 中部つるぎ おどおど（驚き）

SPEAKER_MAP = {
    ("teacher", None): TEACHER_ID,
    ("student", None): STUDENT_ID,
    ("student", "surprise"): STUDENT_SURPRISE,
}

CREDIT_NAMES = ["VOICEVOX:春日部つむぎ"]


def speaker_for(speaker, style=None):
    return SPEAKER_MAP.get((speaker, style)) or SPEAKER_MAP[(speaker, None)]


def _req(path, params=None, method="POST", body=None, timeout=60):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def is_up():
    try:
        _req("/version", method="GET", timeout=2)
        return True
    except Exception:
        return False


def ensure_engine(wait=90):
    """立っていなければヘッドレスで起動する"""
    if is_up():
        return False
    if not ENGINE.exists():
        raise RuntimeError(f"VOICEVOX エンジンが見つかりません: {ENGINE}")
    subprocess.Popen(
        [str(ENGINE), "--host", HOST, "--port", str(PORT)],
        cwd=str(ENGINE.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(wait):
        if is_up():
            return True
        time.sleep(1)
    raise RuntimeError("VOICEVOX エンジンの起動がタイムアウトしました")


def version():
    return json.loads(_req("/version", method="GET"))


def user_dict():
    return json.loads(_req("/user_dict", method="GET"))


def apply_yomi_dict(verbose=False):
    """dict/yomi.json をエンジンのユーザー辞書へ反映（既存は上書き）"""
    spec = json.loads(YOMI.read_text(encoding="utf-8"))
    existing = {w["surface"]: uid for uid, w in user_dict().items()}
    added = updated = 0
    for w in spec["words"]:
        params = {
            "surface": w["surface"],
            "pronunciation": w["pronunciation"],
            "accent_type": w.get("accent_type", 0),
            "word_type": w.get("word_type", "COMMON_NOUN"),
            "priority": w.get("priority", 10),
        }
        uid = existing.get(w["surface"])
        if uid:
            _req(f"/user_dict_word/{uid}", params, method="PUT")
            updated += 1
        else:
            _req("/user_dict_word", params)
            added += 1
        if verbose:
            print(f"    {w['surface']} → {w['pronunciation']}")
    return added, updated


def kana(text, speaker=TEACHER_ID):
    """読み（カタカナ）だけ取る。音声を作らずに読みを検証できる"""
    q = json.loads(_req("/audio_query", {"text": text, "speaker": speaker}))
    return q["kana"]


def plain_kana(text, speaker=TEACHER_ID):
    """アクセント記号を落とした読み"""
    k = kana(text, speaker)
    return k.replace("'", "").replace("_", "").replace("/", "").replace("、", "")


def synth(text, speaker, out_path, speed=1.05, pitch=0.0, intonation=1.0,
          pre=0.05, post=0.25):
    q = json.loads(_req("/audio_query", {"text": text, "speaker": speaker}))
    q["speedScale"] = speed
    q["pitchScale"] = pitch
    q["intonationScale"] = intonation
    q["prePhonemeLength"] = pre
    q["postPhonemeLength"] = post
    wav = _req("/synthesis", {"speaker": speaker}, body=q, timeout=300)
    Path(out_path).write_bytes(wav)
    return out_path
