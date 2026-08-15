"""PoC実行スクリプト。

  python3 src/run_poc.py

パイプライン全体（データ生成 → マッチング → 説明 → 公平性検査）を通す。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fairness import audit, format_report
from matcher import (
    build_transfer_graph,
    match_candidates_for_position,
    match_positions_for_employee,
)
from sample_data import generate


def hr(title: str) -> None:
    print()
    print("=" * 72)
    print(f" {title}")
    print("=" * 72)


def main() -> None:
    employees, positions, transfers = generate()
    graph = build_transfer_graph(transfers)

    print(f"社員 {len(employees)}名 / ポジション {len(positions)}件 "
          f"/ 異動履歴 {len(transfers)}件 を読み込みました")

    # --- ユースケース1: ポジション起点で候補者を探す ---
    pos = positions[0]
    hr(f"ユースケース1: ポジション起点  [{pos.pos_id}] {pos.dept} / {pos.title}")
    print(f"勤務地: {pos.location} / 等級: {pos.grade_min}-{pos.grade_max} "
          f"/ 募集人数: {pos.headcount}")
    print(f"必須スキル: {pos.required_skills}")
    print(f"歓迎スキル: {pos.preferred_skills}")
    if pos.required_certifications:
        print(f"必須資格: {pos.required_certifications}")

    cands, excluded = match_candidates_for_position(pos, employees, graph, top_n=5)
    print(f"\n候補 {len(cands)}名（{len(excluded)}名がハードフィルタで除外）\n")

    for i, r in enumerate(cands, 1):
        e = r.employee
        print(f"{i}. {e.name} ({e.emp_id})  総合スコア {r.total_score:.3f}")
        print(f"   現職: {e.current_dept} {e.current_role} / 等級{e.grade} "
              f"/ {e.location} / 経験{e.experience_years}年")
        print(f"   内訳: スキル{r.skill_score:.2f}(必須充足{r.req_score:.0%}) "
              f"評価{r.comp_score:.2f} 希望{r.wish_score:.2f} "
              f"経路{r.collab_score:.2f} 育成{r.growth_score:.2f}")
        for reason in r.reasons:
            print(f"   - {reason}")
        print()

    # 除外理由の内訳。監査要件
    from collections import Counter
    print("除外理由の内訳:")
    for reason, n in Counter(r for _, r in excluded).most_common():
        print(f"   {n:>3}名  {reason}")

    # --- ユースケース2: 社員起点で異動先を探す ---
    emp = next(e for e in employees if e.career_wish and e.mobility_ok)
    hr(f"ユースケース2: 社員起点  {emp.name} ({emp.emp_id})")
    print(f"現職: {emp.current_dept} {emp.current_role} / 等級{emp.grade}")
    print(f"スキル: {emp.skills}")
    print(f"キャリア希望: 「{emp.career_wish}」\n")

    for i, r in enumerate(match_positions_for_employee(emp, positions, graph), 1):
        p = r.position
        print(f"{i}. [{p.pos_id}] {p.dept} / {p.title}  "
              f"スコア {r.total_score:.3f}")
        for reason in r.reasons:
            print(f"   - {reason}")
        print()

    # --- 公平性検査 ---
    hr("公平性検査（全ポジションの推薦結果を対象）")
    recommended: set[str] = set()
    for p in positions:
        cands, _ = match_candidates_for_position(p, employees, graph, top_n=5)
        recommended.update(r.employee.emp_id for r in cands)

    print(f"全{len(positions)}ポジションの上位5名を集計 → "
          f"のべ{len(recommended)}名が推薦対象\n")
    print(format_report(audit(employees, recommended)))


if __name__ == "__main__":
    main()
