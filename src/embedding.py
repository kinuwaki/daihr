"""スキル名の表記ゆれを吸収する意味的類似度。

## 何を解決するか

現在の skill_score は**完全一致**でスキルを照合している。
そのため次が別物として扱われる。

    「Python」「パイソン」「Python3」
    「データ分析」「データアナリティクス」「統計解析」
    「法人営業」「B2B営業」「BtoB営業」

実データでは表記ゆれが必ず発生する。社内のスキル定義が整っていても、
自己申告欄や職務記述書の自由記述から拾うと揺れる。

## 方針

**埋め込みモデルは任意の依存にする。** 入っていなければ、
文字ベースの類似度（フォールバック）で動く。

理由は二つ。
  1. PoCの「依存ゼロで動く」という利点を壊さない。
     人事担当者に見せる段階で 2GB のモデルを落とさせるのは筋が悪い
  2. 社内データを外に出せない環境が多い。ローカル実行できるモデルを
     選んでいるが、それでも導入判断は組織側にある

## モデルの選定

日本語を含むなら `intfloat/multilingual-e5-large`。
ローカルで動くので**社内データを外部APIに送らずに済む**。
これは人事データを扱ううえで決定的に重要。

E5 系はクエリ側に "query: "、文書側に "passage: " の接頭辞を付ける前提で
学習されている。付け忘れると精度が落ちるため、本モジュールで付与する。
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# 意味的に同一とみなす閾値。これ未満は「別のスキル」として扱う。
#
# _rescale_cosine で「無関係=0.0」に落としてあるので、この閾値は
# 生のコサインではなく引き伸ばし後の値に対するもの。
# 実測値: データ分析↔データ解析 0.71 / 保安管理↔安全管理 0.51 /
#         無関係ペアは全て 0.00
#
# 0.4 にすると強い同義を拾い、無関係は全て落ちる。
# 上げると取りこぼし、下げると誤検出。実データで測り直して調整すること。
SIMILARITY_FLOOR = 0.40

MODEL_NAME = "intfloat/multilingual-e5-large"

_model = None
_model_tried = False


def _load_model():
    """埋め込みモデルを遅延読み込みする。無ければ None を返す。"""
    global _model, _model_tried
    if _model_tried:
        return _model
    _model_tried = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    except Exception:
        # 未インストール、またはモデル未取得。フォールバックで動く
        _model = None
    return _model


def available() -> bool:
    """埋め込みモデルが使える状態か。UIでの表示に使う。"""
    return _load_model() is not None


# ---------------------------------------------------------------- 正規化

# 表記ゆれの主因を機械的に潰す。埋め込みの有無に関わらず前段で効く。
_KANA_MAP = str.maketrans(
    "ァィゥェォッャュョー", "ぁぃぅぇぉっゃゅょー"
)


def normalize_name(name: str) -> str:
    """スキル名の表記を正規化する。

    NFKC で全角英数と半角、全角カナと半角カナを揃え、
    記号・空白を落として小文字化する。
    「Ｐｙｔｈｏｎ３」「python3」「Python 3」が同じ文字列になる。
    """
    s = unicodedata.normalize("NFKC", name)
    s = s.lower()
    s = re.sub(r"[\s　_\-・/／()（）]", "", s)
    return s


# ---------------------------------------------------------------- 類似度

def _char_similarity(a: str, b: str) -> float:
    """文字bigramのJaccard係数。埋め込みが無いときのフォールバック。

    「データ分析」と「データ解析」のような部分一致は拾えるが、
    「Python」と「パイソン」のような表記系の違いは拾えない。
    そこは normalize_name と別名辞書で補う。
    """
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) < 2 or len(b) < 2:
        return 1.0 if a == b else 0.0
    ga = {a[i:i + 2] for i in range(len(a) - 1)}
    gb = {b[i:i + 2] for i in range(len(b) - 1)}
    inter = len(ga & gb)
    union = len(ga | gb)
    return inter / union if union else 0.0


@lru_cache(maxsize=4096)
def _embed(text: str):
    """1件を埋め込む。E5 の接頭辞を付ける。"""
    model = _load_model()
    if model is None:
        return None
    vec = model.encode(f"query: {text}", normalize_embeddings=True)
    return tuple(float(x) for x in vec)


def similarity(a: str, b: str) -> float:
    """2つのスキル名の意味的な近さ。0..1。

    正規化して一致すれば 1.0。
    埋め込みが使えればコサイン類似度、無ければ文字類似度を返す。
    """
    na, nb = normalize_name(a), normalize_name(b)
    if na == nb:
        return 1.0

    va, vb = _embed(a), _embed(b)
    if va is not None and vb is not None:
        # 正規化済みベクトルなので内積がコサイン類似度
        dot = sum(x * y for x, y in zip(va, vb))
        return _rescale_cosine(dot)

    return _char_similarity(na, nb)


# E5 系のモデルは、**無関係な語どうしでもコサインが 0.8 前後**出る。
# 埋め込み空間が原点付近に固まっているためで、これは既知の性質。
#
# 素朴に (cos + 1) / 2 で 0..1 に写すと、無関係な「英語」と「簿記」が
# 0.93 になり、閾値 0.82 を軽く超えてしまう（実測して発見した）。
# 「Python が使える人が営業職に推薦される」ことになるので致命的。
#
# そこで、無関係語のコサインを 0 に、完全一致を 1 に写す線形変換をかける。
# COSINE_BASELINE は「無関係な語どうしのコサイン」の実測値。
#
# multilingual-e5-large で、明らかに無関係なスキル12語の全66ペアを実測:
#   最小 0.728 / 中央 0.798 / 95パーセンタイル 0.845 / 最大 0.878
# 同義ペア（データ分析↔データ解析 等）は 0.879〜0.963。
#
# 無関係の最大(0.878)と同義の最小(0.879)がほぼ接しており、両者は
# 完全には分離できない。安全側（無関係を通さない側）に倒して 0.87 とする。
# その代償として、弱い同義（法人営業↔B2B営業 = 0.879）は拾えるが
# ぎりぎりになる。
#
# **モデルを変えたら必ず測り直すこと。** この値はモデル固有である。
COSINE_BASELINE = 0.87


def _rescale_cosine(cos: float) -> float:
    """コサインを、無関係=0・同一=1 になるよう引き伸ばす。"""
    if cos <= COSINE_BASELINE:
        return 0.0
    return (cos - COSINE_BASELINE) / (1.0 - COSINE_BASELINE)


def best_match(target: str, candidates: dict[str, int],
               floor: float = SIMILARITY_FLOOR) -> tuple[str | None, float]:
    """候補のうち target に最も近いものを返す。(名前, 類似度)。

    閾値未満しか無ければ (None, 最高類似度) を返す。
    呼び出し側は「見つからなかった」と扱う。
    """
    if not candidates:
        return None, 0.0
    if target in candidates:
        return target, 1.0

    best, best_sim = None, 0.0
    for name in candidates:
        sim = similarity(target, name)
        if sim > best_sim:
            best, best_sim = name, sim
    return (best, best_sim) if best_sim >= floor else (None, best_sim)


def resolve_level(target: str, skills: dict[str, int],
                  floor: float = SIMILARITY_FLOOR) -> tuple[int, str | None, float]:
    """target に対応する習熟度を、表記ゆれを吸収して取り出す。

    戻り値は (習熟度, 一致したスキル名, 類似度)。
    見つからなければ (0, None, 類似度)。

    完全一致を優先し、無い場合だけ類似検索する。
    類似度が閾値ぎりぎりの場合に習熟度をそのまま採用すると
    誤った適合判定になるため、**類似度で習熟度を割り引く**。
    """
    if target in skills:
        return skills[target], target, 1.0

    name, sim = best_match(target, skills, floor)
    if name is None:
        return 0, None, sim

    # 類似度で割り引く。完全一致でない以上、確信度を反映させる
    return int(round(skills[name] * sim)), name, sim
