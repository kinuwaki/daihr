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


# 教科書・動画に載せている数値。重みを変えたらここも更新すること
# （更新し忘れると教科書と実装がずれるので、このテストが落ちて気づける）
expected = {0.0: None, 0.25: None, 0.5: 0.394, 1.0: 0.608}
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


# 検出力の基準。ハードフィルタ（転居可否など）が増えるほど候補が絞られ、
# 属性と無相関な条件がノイズとして効いて検出力は下がる。
# 60% は「20回中12回は検出できる」水準で、公平性検査としては実用範囲。
# ここを上げたければ、候補の母数（推薦対象の人数）を増やす必要がある。
power = sweep(inject_bias)
check("実バイアス注入時の検出が 60% 以上", power >= 12, f"{power}/20 = {power/20:.0%}")

# ---------------------------------------------------------------- 4.5
print("\n── 4.5 人的つながり（相関図） ──")

from network import NetworkContext

net = NetworkContext(employees, transfers)
summ = net.summary()
check("グラフが構築されている", summ["nodes"] > 0, f"{summ['nodes']}名 / {summ['edges']}辺")

# 自分自身はつながりに数えない
self_loops = sum(1 for a, ns in net.graph.items() if a in ns)
check("自己ループが無い", self_loops == 0, f"{self_loops}件")

# つながりが無い相手には 0 を返す（中立0.5ではない）
lonely = [e for e in employees if not net.graph.get(e.emp_id)]
if lonely:
    sc, n = net.score(lonely[0].emp_id, positions[0].dept)
    check("つながりが無ければ 0.0", sc == 0.0 and n == 0, f"score={sc}")
else:
    check("つながりが無ければ 0.0", True, "該当者なし（全員に接点あり）")

# スコアは単調（人数が増えれば下がらない）
vals = [1.0 - 0.45 ** min(k, 8) for k in range(1, 10)]
check("人数に対して単調増加", all(a <= b for a, b in zip(vals, vals[1:])))

# ---------------------------------------------------------------- 4.6
print("\n── 4.6 正規化（設定重みと実効重みの一致） ──")

import statistics

from matcher import (SCORE_STATS, WEIGHTS, competency_score, growth_score,
                     hard_filter, normalize, wish_score)
from matcher import collab_score as _collab
from matcher import skill_score as _skill

raw = {k: [] for k in WEIGHTS}
for p_ in positions:
    for e_ in employees:
        okf, _ = hard_filter(e_, p_)
        if not okf:
            continue
        sk_, _, _, _ = _skill(e_, p_)
        cp_, _, _ = competency_score(e_, p_)
        raw["skill"].append(sk_)
        raw["comp"].append(cp_)
        raw["wish"].append(wish_score(e_, p_))
        raw["collab"].append(_collab(e_, p_, graph))
        raw["growth"].append(growth_score(e_, p_))
        raw["network"].append(net.score(e_.emp_id, p_.dept)[0])

# 正規化後の実効重み = 重み × 平均寄与 の構成比
eff = {k: WEIGHTS[k] * statistics.mean([normalize(k, x) for x in v])
       for k, v in raw.items()}
total_eff = sum(eff.values())
worst_gap = max(abs(eff[k] / total_eff - WEIGHTS[k]) for k in WEIGHTS)
check("設定重みと実効重みの差が 5ポイント以内", worst_gap <= 0.05,
      f"最大差 {worst_gap:.1%}")

# 正規化は単調変換でなければならない（スコア内部の順序を変えない）
mono = all(
    normalize(k, a) <= normalize(k, b)
    for k in SCORE_STATS
    for a, b in zip([0.0, 0.2, 0.4, 0.6, 0.8], [0.2, 0.4, 0.6, 0.8, 1.0])
)
check("正規化が単調変換である", mono)

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
