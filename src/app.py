"""異動支援AI — 人事担当者向けUI（PoC）

  pip install streamlit
  streamlit run src/app.py

設計方針:
  - AIは「候補の発見と根拠の提示」まで。決定は人が行う。
    そのためスコアは常に内訳と根拠をセットで表示し、
    「なぜこの順位か」を担当者が検証できるようにしている。
  - 除外された人の理由も見られるようにしてある（監査要件）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from fairness import MIN_GROUP_SIZE, audit
from matcher import (
    DAMPING_FLOOR,
    SKILL_FLOOR,
    WEIGHTS,
    build_transfer_graph,
    match_candidates_for_position,
    match_positions_for_employee,
)
from sample_data import DEPT_SEGMENT, generate

st.set_page_config(page_title="異動支援AI (PoC)", page_icon="🔁", layout="wide")


@st.cache_data
def load(seed: int):
    return generate(seed=seed)


def score_bar(label: str, value: float, weight: float) -> None:
    st.caption(f"{label}  {value:.2f}  (重み{weight:.2f})")
    st.progress(min(1.0, max(0.0, value)))


def render_candidate(rank: int, r) -> None:
    e = r.employee
    with st.container(border=True):
        head, score = st.columns([4, 1])
        with head:
            st.markdown(f"**{rank}. {e.name}**  `{e.emp_id}`")
            seg = DEPT_SEGMENT.get(e.current_dept, "")
            st.caption(
                f"{seg} ／ {e.current_dept} {e.current_role} / 等級{e.grade} / "
                f"{e.location} / 経験{e.experience_years}年"
            )
        with score:
            st.metric("総合", f"{r.total_score:.3f}")

        left, right = st.columns([1, 1])
        with left:
            score_bar("スキル", r.skill_score, WEIGHTS["skill"])
            score_bar("評価（コンピテンシー）", r.comp_score, WEIGHTS["comp"])
            score_bar("本人希望", r.wish_score, WEIGHTS["wish"])
            score_bar("異動経路", r.collab_score, WEIGHTS["collab"])
            score_bar("育成機会", r.growth_score, WEIGHTS["growth"])
            st.caption(f"必須スキル充足率 **{r.req_score:.0%}**")
        with right:
            st.markdown("**推薦根拠**")
            for reason in r.reasons:
                st.markdown(f"- {reason}")
            if e.career_wish:
                st.info(f"本人希望: 「{e.career_wish}」", icon="💬")


def main() -> None:
    st.title("🔁 社内異動支援AI — PoC")
    st.caption(
        "AIは候補の発見と根拠の提示までを担当します。"
        "**異動の決定は必ず人が行ってください。**"
    )

    with st.sidebar:
        st.header("設定")
        seed = st.number_input("データseed", 0, 999, 42,
                               help="ダミーデータの乱数シード")
        top_n = st.slider("表示する候補数", 3, 20, 5)

        st.divider()
        st.subheader("スコア重み")
        st.caption("人事の方針に合わせて調整してください")
        WEIGHTS["skill"] = st.slider("スキル", 0.0, 1.0, WEIGHTS["skill"], 0.05)
        WEIGHTS["comp"] = st.slider("評価（コンピテンシー）", 0.0, 1.0,
                                    WEIGHTS["comp"], 0.05)
        WEIGHTS["wish"] = st.slider("本人希望", 0.0, 1.0, WEIGHTS["wish"], 0.05)
        WEIGHTS["collab"] = st.slider("異動経路", 0.0, 1.0, WEIGHTS["collab"], 0.05)
        WEIGHTS["growth"] = st.slider("育成機会", 0.0, 1.0, WEIGHTS["growth"], 0.05)

        st.divider()
        st.caption(
            f"必須スキル充足率が **{SKILL_FLOOR:.0%}** 未満の候補は"
            f"自動的に除外されます。通過後も充足率に応じて"
            f"スコアを減衰させます（下限{DAMPING_FLOOR:.0%}）。"
        )

    employees, positions, transfers = load(int(seed))
    graph = build_transfer_graph(transfers)

    st.sidebar.divider()
    st.sidebar.metric("社員数", len(employees))
    st.sidebar.metric("募集ポジション", len(positions))
    st.sidebar.metric("異動履歴", len(transfers))

    tab1, tab2, tab3 = st.tabs(
        ["📋 ポジション起点", "👤 社員起点", "⚖️ 公平性検査"]
    )

    # --- ポジション起点 ---
    with tab1:
        labels = {
            f"[{p.pos_id}] {DEPT_SEGMENT.get(p.dept, '')} / {p.dept} / {p.title}": p
            for p in positions
        }
        pos = labels[st.selectbox("募集ポジション", list(labels))]

        c1, c2, c3 = st.columns(3)
        c1.metric("勤務地", pos.location)
        c2.metric("等級", f"{pos.grade_min} 〜 {pos.grade_max}")
        c3.metric("募集人数", pos.headcount)

        st.markdown(
            f"**必須スキル**: "
            + "、".join(f"`{k}`(要{v})" for k, v in pos.required_skills.items())
        )
        if pos.preferred_skills:
            st.markdown(
                "**歓迎スキル**: "
                + "、".join(f"`{k}`({v})" for k, v in pos.preferred_skills.items())
            )
        if pos.required_competencies:
            st.markdown(
                "**求めるコンピテンシー**: "
                + "、".join(f"`{k}`(要{v})"
                           for k, v in pos.required_competencies.items())
            )
        if pos.required_certifications:
            st.markdown(f"**必須資格**: {'、'.join(pos.required_certifications)}")

        st.divider()
        cands, excluded = match_candidates_for_position(
            pos, employees, graph, top_n=top_n
        )

        if not cands:
            st.warning(
                "条件に合う候補がいません。必須スキルの要件、または"
                "等級レンジの見直しを検討してください。"
            )
        else:
            st.success(f"候補 {len(cands)}名（{len(excluded)}名を除外）")
            for i, r in enumerate(cands, 1):
                render_candidate(i, r)

        with st.expander(f"除外された {len(excluded)}名の理由（監査用）"):
            from collections import Counter
            for reason, n in Counter(r for _, r in excluded).most_common():
                st.markdown(f"- **{n}名** — {reason}")
            st.caption(
                "「なぜ推薦されなかったか」を説明できることは、"
                "本人開示請求や労組対応で必要になります。"
            )

    # --- 社員起点 ---
    with tab2:
        movable = [e for e in employees if e.mobility_ok]
        labels = {f"{e.name} ({e.emp_id}) — {e.current_dept}": e for e in movable}
        emp = labels[st.selectbox("社員", list(labels))]

        c1, c2, c3 = st.columns(3)
        c1.metric("現部署", emp.current_dept)
        c2.metric("等級", emp.grade)
        c3.metric("経験年数", f"{emp.experience_years}年")

        st.markdown("**保有スキル**")
        st.markdown("　".join(
            f"`{k}` {'★' * v}" for k, v in
            sorted(emp.skills.items(), key=lambda kv: -kv[1])
        ))
        if emp.career_wish:
            st.info(f"キャリア希望: 「{emp.career_wish}」", icon="💬")
        else:
            st.warning("キャリア希望が未登録です。意向確認を推奨します。")

        st.divider()
        results = match_positions_for_employee(emp, positions, graph, top_n=top_n)
        if not results:
            st.warning("条件に合うポジションがありません。")
        for i, r in enumerate(results, 1):
            p = r.position
            with st.container(border=True):
                a, b = st.columns([4, 1])
                a.markdown(f"**{i}. [{p.pos_id}] {p.dept} / {p.title}**")
                a.caption(f"{p.location} / 等級{p.grade_min}-{p.grade_max}")
                b.metric("総合", f"{r.total_score:.3f}")
                for reason in r.reasons:
                    st.markdown(f"- {reason}")

    # --- 公平性検査 ---
    with tab3:
        st.markdown(
            "全ポジションの推薦結果を集計し、保護属性による偏りを検査します。"
        )
        st.caption(
            "保護属性はマッチングの入力に一切使っていません。"
            "それでも偏りが出る場合、他の特徴量が代理変数になっています。"
        )

        recommended = set()
        for p in positions:
            c, _ = match_candidates_for_position(p, employees, graph, top_n=top_n)
            recommended.update(r.employee.emp_id for r in c)

        st.metric("推薦対象となった社員（のべ）", f"{len(recommended)}名")
        st.divider()

        for rep in audit(employees, recommended):
            ratio = rep["ratio"]
            p_val = rep["p_value"]
            icon = {"OK": "✅", "要調査": "🚨"}.get(rep["verdict"], "⚠️")
            st.subheader(f"{icon} {rep['attribute']} — {rep['verdict']}")

            a, b = st.columns(2)
            a.metric("Parity ratio", f"{ratio:.2f}" if ratio else "N/A",
                     help="最小推薦率 ÷ 最大推薦率。0.8未満で4/5ルール抵触")
            b.metric("p値 (Bonferroni補正済)",
                     f"{p_val:.3f}" if p_val is not None else "N/A",
                     help="0.05未満なら偶然では説明しにくい")

            for val, rate in sorted(rep["rates"].items(), key=lambda kv: -kv[1]):
                picked, total = rep["counts"][val]
                small = " ⚠️標本不足" if total < MIN_GROUP_SIZE else ""
                st.caption(f"{val} — {picked}/{total} ({rate:.1%}){small}")
                st.progress(rate)

            if rep["verdict"] == "要調査":
                st.error(
                    "統計的に有意な偏りです。特徴量に代理変数が"
                    "混入していないか確認してください。"
                )
            elif rep["verdict"] == "偏りあり(有意でない)":
                st.warning(
                    "比率は基準を下回りますが、統計的には偶然の範囲内です。"
                    "標本を増やして再検査してください。"
                )
            elif rep["verdict"] == "判定保留(標本不足)":
                st.info(
                    f"{MIN_GROUP_SIZE}名未満の群があるため判定できません。"
                )
            st.divider()


if __name__ == "__main__":
    main()
