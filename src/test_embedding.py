"""スキル名の表記ゆれ吸収を検証する。

  python3 src/test_embedding.py

埋め込みモデルの有無で挙動が変わるので、両方で意味のある検証をする。
モデルが無い環境では「フォールバックが壊れていないこと」だけを見る。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from embedding import (SIMILARITY_FLOOR, available, normalize_name,
                       resolve_level, similarity)

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    if not cond:
        ok = False
    print(("OK " if cond else "NG ") + label + (f"  — {detail}" if detail else ""))


# 実データで実際に起きる表記ゆれ。
# 「同じスキルとして扱ってほしい」ペア
SAME = [
    ("Python", "ｐｙｔｈｏｎ"),
    ("Python", "Python "),
    ("データ分析", "データ 分析"),
    ("B2B営業", "Ｂ２Ｂ営業"),
    ("SQL", "ｓｑｌ"),
]

# 意味は近いが表記が違うペア。
#
# 実測すると、無関係ペアのコサイン最大(0.878)と同義ペアの最小(0.879)が
# ほぼ接しており、**単一の閾値では完全に分離できない**。
# 誤って同一視する方が実害が大きい（Pythonができる人が営業職に推薦される）
# ので、安全側に倒している。その結果、弱い同義は拾えない。
#
# 「拾えてほしい」ものと「拾えなくてもよい」ものを分けて検証する。
SEMANTIC_STRONG = [        # 語幹が共通。拾えるべき
    ("データ分析", "データ解析"),
    ("保安管理", "安全管理"),
]
SEMANTIC_WEAK = [          # 語形が違う。現状の閾値では拾えない（既知の限界）
    ("法人営業", "B2B営業"),
    ("プラント設計", "設備設計"),
]

# 別のスキルとして扱ってほしいペア。ここを同一視したら誤り
DIFFERENT = [
    ("Python", "法人営業"),
    ("財務会計", "導管技術"),
    ("採用", "発電所運用"),
    ("英語", "簿記"),
]

print(f"埋め込みモデル: {'利用可' if available() else '未導入（フォールバック）'}")
print(f"閾値: {SIMILARITY_FLOOR}")

print("\n── 1. 正規化で吸収できる表記ゆれ ──")
for a, b in SAME:
    check(f"{a!r} == {b!r}", normalize_name(a) == normalize_name(b),
          f"{normalize_name(a)!r} vs {normalize_name(b)!r}")

print("\n── 2. 別スキルを同一視していないか（最重要） ──")
# ここが壊れると「Pythonができる人が営業職に推薦される」ことになる
for a, b in DIFFERENT:
    sim = similarity(a, b)
    check(f"{a!r} != {b!r}", sim < SIMILARITY_FLOOR, f"類似度 {sim:.2f}")

print("\n── 3. 意味的に近い表記ゆれ ──")
if available():
    for a, b in SEMANTIC_STRONG:
        sim = similarity(a, b)
        check(f"{a!r} ~ {b!r}", sim >= 0.4, f"類似度 {sim:.2f}")
    print("   （以下は現状の閾値では拾えない。既知の限界として記録）")
    for a, b in SEMANTIC_WEAK:
        print(f"   -- {a!r} ~ {b!r}  類似度 {similarity(a, b):.2f}")
else:
    for a, b in SEMANTIC_STRONG + SEMANTIC_WEAK:
        print(f"-- {a!r} ~ {b!r}  類似度 {similarity(a, b):.2f}（モデル未導入のため参考値）")

print("\n── 4. 習熟度の解決 ──")
skills = {"データ分析": 4, "法人営業": 3, "Python": 5}

lv, name, sim = resolve_level("データ分析", skills)
check("完全一致は習熟度をそのまま返す", lv == 4 and sim == 1.0, f"{lv} ({name})")

lv, name, sim = resolve_level("導管技術", skills)
check("無関係なスキルは 0", lv == 0 and name is None, f"{lv} (類似{sim:.2f})")

lv, name, sim = resolve_level("ｐｙｔｈｏｎ", skills)
check("正規化で一致すれば習熟度を返す", lv == 5, f"{lv} ({name} 類似{sim:.2f})")

print("\n" + "=" * 52)
print("✓ 全て一致" if ok else "✗ 表記ゆれの扱いに問題があります")
sys.exit(0 if ok else 1)
