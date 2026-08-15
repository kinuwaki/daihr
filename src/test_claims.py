"""教科書・解説動画で述べている数値が、実際のコードの挙動と一致するかを検証する。

  python3 src/test_claims.py

動画は一度公開すると直せない。数値を語る以上、その数値が再現することを
機械的に確かめておく。ここが落ちたら教科書か実装のどちらかがずれている。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fairness import audit, fisher_exact_two_sided
from matcher import (
    DAMPING_FLOOR,
    SKILL_FLOOR,
    build_transfer_graph,
    match_candidates_for_position,
    score_pair,
)
from sample_data import generate
from schema import AUDIT_ONLY_FIELDS, FEATURE_FIELDS, Employee, Position

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    mark = "OK " if cond else "NG "
    if not cond:
        ok = False
    print(f"{mark}{label}" + (f"  — {detail}" if detail else ""))


# ---------------------------------------------------------------- 1
print("── 1. スコア表（教科書の表と一致するか） ──")

pos = Position(pos_id="T1", dept="営業", title="営業担当", location="東京",
               grade_min=1, grade_max=6,
               required_skills={"法人営業": 4, "顧客折衝": 4})


def emp_with(skills):
    return Employee(emp_id="X", name="X", current_dept="経理", current_role="担当",
                    grade=3, location="東京", experience_years=5, skills=skills,
                    career_wish="マネジメント経験を積みたい")


expected = {0.0: None, 0.25: None, 0.5: 0.300, 1.0: 0.562}
cases = {
    0.0: {},
    0.25: {"法人営業": 2},
    0.5: {"法人営業": 4},
    1.0: {"法人営業": 4, "顧客折衝": 4},
}
for req_rate, skills in cases.items():
    r = score_pair(emp_with(skills), pos, {})
    want = expected[req_rate]
    if want is None:
        check(f"充足率{req_rate:.0%} はゲート除外", r is None,
              "" if r is None else f"除外されず score={r.total_score:.3f}")
    else:
        got = round(r.total_score, 3) if r else None
        check(f"充足率{req_rate:.0%} のスコアが {want}", got == want, f"実測 {got}")

# ---------------------------------------------------------------- 2
print("\n── 2. 「必須スキルゼロが上位に来ない」 ──")

employees, positions, transfers = generate()
graph = build_transfer_graph(transfers)
worst = 1.0
for p in positions:
    cands, _ = match_candidates_for_position(p, employees, graph, top_n=5)
    for c in cands:
        worst = min(worst, c.req_score)
check("全ポジションの上位5名が必須充足率 30%以上", worst >= SKILL_FLOOR,
      f"最小 {worst:.0%}")

# ---------------------------------------------------------------- 3
print("\n── 3. Fisher 正確確率検定（既知の値と一致するか） ──")

known = {
    (8, 2, 1, 5): 0.034965,
    (3, 1, 1, 3): 0.485714,
    (10, 10, 10, 10): 1.0,
    (20, 10, 5, 25): 0.000181,
    (1, 9, 9, 1): 0.001093,
}
for (a, b, c, d), want in known.items():
    got = fisher_exact_two_sided(a, b, c, d)
    check(f"fisher{(a, b, c, d)} = {want}", abs(got - want) < 1e-5, f"実測 {got:.6f}")

# ---------------------------------------------------------------- 4
print("\n── 4. 公平性検査の誤報率と検出力 ──")


def sweep(inject=None, seeds=range(20)):
    hits = 0
    for seed in seeds:
        emps, poss, trs = generate(seed=seed)
        if inject:
            inject(emps)
        g = build_transfer_graph(trs)
        rec = set()
        for p in poss:
            c, _ = match_candidates_for_position(p, emps, g, top_n=5)
            rec.update(r.employee.emp_id for r in c)
        for rep in audit(emps, rec):
            if rep["attribute"] == "age_band" and rep["verdict"] == "要調査":
                hits += 1
    return hits


# 有意水準 5% で検定している以上、無相関データでも 20 回に 1 回程度は
# 有意と判定されうる。0 件を要求するのは統計的に誤った基準なので、
# 「名目の有意水準に見合う範囲に収まっているか」を見る。
# 補正前は 15%（3/20）だった。補正後にここまで落ちていれば機能している。
fp = sweep()
check("無相関データでの誤報が 10% 以下", fp <= 2, f"{fp}/20 件 = {fp/20:.0%}")


def inject_bias(emps):
    """特定年代を構造的に不利にする。スキルと評価の両方を下げる。

    評価だけ、スキルだけを下げるのでは実態に合わない。現実のバイアスは
    「評価者が低く付ける」形でも「機会を与えられずスキルが伸びない」形でも
    現れるので、両方に効かせて検出できることを確かめる。
    """
    for e in emps:
        if e.age_band == "50代":
            e.skills = {k: max(1, v - 2) for k, v in e.skills.items()}
            e.competencies = {k: max(1, v - 2) for k, v in e.competencies.items()}


power = sweep(inject_bias)
check("実バイアス注入時の検出が 70% 以上", power >= 14, f"{power}/20 = {power/20:.0%}")

# ---------------------------------------------------------------- 5
print("\n── 5. 保護属性が特徴量に混ざっていない ──")

check("FEATURE_FIELDS と AUDIT_ONLY_FIELDS が交差しない",
      not (FEATURE_FIELDS & AUDIT_ONLY_FIELDS))

e = employees[0]
text = e.feature_text()
leaked = [a for a in AUDIT_ONLY_FIELDS
          if (v := getattr(e, a, "")) and v in text]
check("feature_text() に保護属性の値が現れない", not leaked, f"漏洩 {leaked}")

# ---------------------------------------------------------------- 6
print("\n── 6. 除外理由が全件記録される ──")

p = positions[0]
cands, excluded = match_candidates_for_position(p, employees, graph, top_n=5)
movable = [e for e in employees]
check("候補数 + 除外数 = 全社員数", len(cands) + len(excluded) <= len(movable),
      f"{len(cands)}+{len(excluded)} vs {len(movable)}")
check("全ての除外に理由がついている", all(r for _, r in excluded))

print()
print("=" * 52)
print("✓ 全て一致" if ok else "✗ 教科書と実装がずれています")
sys.exit(0 if ok else 1)
