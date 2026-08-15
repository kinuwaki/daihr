"""異動候補のマッチングエンジン。

構成:
  1. ハードフィルタ  … 等級・勤務地・必須資格・異動可否をルールで判定
  2. スキル適合スコア … 必須/歓迎スキルの充足度
  3. 協調シグナル    … 過去の異動履歴から見た経路の一般性
  4. 希望整合スコア  … 本人のキャリア希望との一致
  5. 合成 & 再ランキング

意図的に「埋め込みモデル無し」でも動くようにしてある。
外部APIを繋ぐ前にロジックの妥当性を人事担当者と確認できる状態を先に作るため。
embedding を使う場合は skill_score を意味的類似度に差し替える（README参照）。
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from schema import Employee, Position, TransferRecord

# 各スコアの重み。人事と調整する前提で外出ししてある
WEIGHTS = {
    "skill": 0.35,
    "comp": 0.20,     # コンピテンシー評価との適合
    "wish": 0.20,
    "collab": 0.15,
    "growth": 0.10,
}

# 必須スキルの充足率がこれ未満の候補は推薦しない。
# 加重和だけで順位付けすると「必須スキルがゼロなのに本人希望と
# 過去の異動経路だけで上位に来る」候補が発生し、人事担当者の信頼を失う。
SKILL_FLOOR = 0.30

# 必須スキル充足率が低いときに総合スコアを減衰させる係数の下限。
# ゲートを通過しても、スキル不足の候補が満点候補と並ばないようにする。
DAMPING_FLOOR = 0.40


@dataclass
class MatchResult:
    employee: Employee
    position: Position
    total_score: float
    skill_score: float
    req_score: float          # 必須スキルのみの充足率。ゲート・減衰の判定に使う
    comp_score: float         # コンピテンシー評価との適合
    wish_score: float
    collab_score: float
    growth_score: float
    matched_skills: list[str]
    missing_skills: list[tuple[str, int, int]]   # (スキル名, 必要, 現在)
    met_competencies: list[str] = field(default_factory=list)
    missing_competencies: list = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def gap_summary(self) -> str:
        if not self.missing_skills:
            return "必須スキルは充足"
        return "、".join(
            f"{name}(要{need}/現{have})" for name, need, have in self.missing_skills
        )


def hard_filter(emp: Employee, pos: Position) -> tuple[bool, str]:
    """通過可否と、落ちた理由を返す。監査ログに残せるよう理由を明示する。"""
    if not emp.mobility_ok:
        return False, "異動不可フラグ"
    if emp.current_dept == pos.dept:
        return False, "同一部署"
    if not (pos.grade_min <= emp.grade <= pos.grade_max):
        return False, f"等級不一致(本人{emp.grade}/募集{pos.grade_min}-{pos.grade_max})"
    missing_certs = [c for c in pos.required_certifications
                     if c not in emp.certifications]
    if missing_certs:
        return False, f"必須資格未保有({'、'.join(missing_certs)})"
    return True, ""


def skill_score(emp: Employee, pos: Position) -> tuple[float, float, list[str], list]:
    """必須スキルの充足度を主、歓迎スキルを従として評価。

    戻り値の req_score（必須スキルのみの充足率）を分離して返すのは、
    ゲート判定と減衰にこの値だけを使うため。歓迎スキルで必須スキルの
    不足を埋め合わせられてしまうと、ゲートの意味が無くなる。
    """
    matched, missing = [], []
    req_total = 0.0
    for name, need in pos.required_skills.items():
        have = emp.skills.get(name, 0)
        ratio = min(1.0, have / need) if need else 1.0
        req_total += ratio
        if have >= need:
            matched.append(name)
        else:
            missing.append((name, need, have))
    req_score = req_total / len(pos.required_skills) if pos.required_skills else 1.0

    pref_total = 0.0
    for name, need in pos.preferred_skills.items():
        have = emp.skills.get(name, 0)
        if have > 0:
            pref_total += min(1.0, have / need) if need else 1.0
            if have >= need:
                matched.append(name)
    pref_score = (pref_total / len(pos.preferred_skills)
                  if pos.preferred_skills else 0.0)

    combined = 0.75 * req_score + 0.25 * pref_score
    return combined, req_score, matched, missing


def competency_score(emp: Employee, pos: Position) -> tuple[float, list, list]:
    """人事評価のコンピテンシー項目と、ポジションが求める水準の適合。

    スキル（何ができるか）とは別軸で、行動特性の適合を見る。
    戻り値は (スコア, 満たした項目, 不足項目[(名, 要, 現)])。

    評価データを使う以上、次の三つを守る:
      1. 総合評価点は使わない。項目別評価だけを使う（選別にしないため）
      2. 本人同意が無ければ参照しない（usable_competencies が空を返す）
      3. 評価が無い人を不利にしない。データが無い場合は中立の 0.5 を返す

    3 が重要で、ここをゼロにすると「評価がまだ無い異動直後の社員」や
    「同意していない社員」が構造的に候補から外れる。
    """
    need = pos.required_competencies
    if not need:
        return 0.5, [], []

    have = emp.usable_competencies()
    if not have:
        # 同意が無い、または評価データが無い。中立に倒す
        return 0.5, [], []

    met, missing, total = [], [], 0.0
    for name, want in need.items():
        got = have.get(name, 0)
        if got == 0:
            # その項目の評価が存在しない。中立扱いにして不足に数えない
            total += 0.5
            continue
        total += min(1.0, got / want) if want else 1.0
        (met if got >= want else missing).append(
            name if got >= want else (name, want, got))
    return total / len(need), met, missing


def wish_score(emp: Employee, pos: Position) -> float:
    """キャリア希望とポジションの整合。

    PoCではキーワード照合。本番では埋め込み類似度に差し替える。
    希望が未記入の場合は中立値を返す（希望を書かない人を不利にしない）。
    """
    if not emp.career_wish:
        return 0.5

    keywords = {
        "データ": ["データ分析", "SQL", "Python", "統計"],
        "海外": ["海外", "グローバル", "英語"],
        "マネジメント": ["リーダー", "課長", "管理", "マネージャ"],
        "専門": ["専門", "エキスパート", "スペシャリスト"],
        "幅": [],
        "顧客": ["営業", "顧客", "カスタマー"],
        "企画": ["企画", "戦略", "マーケティング"],
    }
    target = f"{pos.dept} {pos.title} {pos.description} " + \
             " ".join(pos.required_skills) + " " + " ".join(pos.preferred_skills)

    for key, terms in keywords.items():
        if key in emp.career_wish:
            if not terms:                      # 「幅を広げたい」= 異動自体が目的
                return 0.8
            if any(t in target for t in terms):
                return 1.0
            return 0.35
    return 0.5


def build_transfer_graph(transfers: list[TransferRecord]) -> dict:
    """部署間の異動経路の頻度。個人単位ではなく部署単位に集約する。

    個人の異動履歴をそのまま推薦に使うとプライバシー上の問題が出るため、
    「どの部署からどの部署への異動が一般的か」という集約統計のみ使う。
    """
    graph: dict[str, Counter] = defaultdict(Counter)
    for t in transfers:
        graph[t.from_dept][t.to_dept] += 1
    return graph


def collab_score(emp: Employee, pos: Position, graph: dict) -> float:
    """過去に同じ経路の異動が多いほど高スコア。

    注意: これは「過去の慣行」の再現なので、過去が偏っていれば偏りも再現する。
    重みを控えめ(0.20)にしてあるのはそのため。
    """
    outgoing = graph.get(emp.current_dept)
    if not outgoing:
        return 0.5
    total = sum(outgoing.values())
    count = outgoing.get(pos.dept, 0)
    if total == 0:
        return 0.5
    # 最頻経路を1.0とする正規化
    return count / max(outgoing.values()) if max(outgoing.values()) else 0.5


def growth_score(emp: Employee, pos: Position) -> float:
    """成長機会としての妥当性。

    スキルが完全に一致 = 成長がない、乖離が大きすぎ = 無理がある。
    「少し背伸び」を最も高く評価する。異動を育成機会と捉える設計。
    """
    if not pos.required_skills:
        return 0.5
    gaps = []
    for name, need in pos.required_skills.items():
        have = emp.skills.get(name, 0)
        gaps.append(need - have)
    avg_gap = sum(gaps) / len(gaps)
    # ギャップ1.0前後を最良とする山形の関数
    if avg_gap <= 0:
        return 0.55                      # 完全充足。悪くはないが伸びしろが小さい
    if avg_gap <= 1.5:
        return 1.0 - abs(avg_gap - 1.0) * 0.3
    return max(0.0, 0.7 - (avg_gap - 1.5) * 0.35)


def score_pair(emp: Employee, pos: Position, graph: dict) -> "MatchResult | None":
    """1組の (社員, ポジション) を採点する。ゲートで落ちた場合は None。

    合成は「加重和 × 必須スキル減衰」。純粋な加重和だと必須スキルゼロでも
    他のスコアで上位に来てしまうため、必須スキル充足率を掛けて抑える。
    """
    sk, req, matched, missing = skill_score(emp, pos)

    # ゲート: 必須スキルが決定的に足りない候補は推薦対象から外す
    if req < SKILL_FLOOR:
        return None

    cp, met_c, miss_c = competency_score(emp, pos)
    wi = wish_score(emp, pos)
    co = collab_score(emp, pos, graph)
    gr = growth_score(emp, pos)

    weighted = (WEIGHTS["skill"] * sk + WEIGHTS["comp"] * cp
                + WEIGHTS["wish"] * wi + WEIGHTS["collab"] * co
                + WEIGHTS["growth"] * gr)

    # 必須スキル充足率で減衰。DAMPING_FLOOR より下には落とさず、
    # ゲートを通った候補同士の相対順位を保つ
    damping = DAMPING_FLOOR + (1.0 - DAMPING_FLOOR) * req
    total = weighted * damping

    r = MatchResult(
        employee=emp, position=pos, total_score=total,
        skill_score=sk, req_score=req, comp_score=cp, wish_score=wi,
        collab_score=co, growth_score=gr,
        matched_skills=matched, missing_skills=missing,
        met_competencies=met_c, missing_competencies=miss_c,
    )
    r.reasons = build_reasons(r)
    return r


def build_reasons(r: "MatchResult") -> list[str]:
    """人事担当者に提示する根拠。スコアだけでは使えないので言語化する。"""
    reasons = []
    if r.matched_skills:
        reasons.append(f"適合スキル: {'、'.join(r.matched_skills[:4])}")
    if r.met_competencies:
        reasons.append(
            f"評価で水準を満たすコンピテンシー: {'、'.join(r.met_competencies[:3])}")
    if r.missing_competencies:
        gap = "、".join(f"{n}(要{w}/現{g})" for n, w, g in r.missing_competencies[:3])
        reasons.append(f"コンピテンシーが水準未達: {gap}")
    if r.position.required_competencies and not r.employee.eval_consent:
        reasons.append("※評価データの利用同意が未取得。評価は考慮していない")
    if r.wish_score >= 0.8 and r.employee.career_wish:
        reasons.append(f"本人希望と整合: 「{r.employee.career_wish}」")
    if r.collab_score >= 0.7:
        reasons.append(
            f"{r.employee.current_dept}→{r.position.dept} は過去に実績のある異動経路"
        )
    if r.growth_score >= 0.85:
        reasons.append("適度なストレッチがあり育成機会として有効")
    if r.missing_skills:
        label = "要育成" if r.req_score >= 0.6 else "要育成(不足大)"
        reasons.append(f"{label}: {r.gap_summary()}")
    if not r.employee.career_wish:
        reasons.append("※本人のキャリア希望が未登録。意向確認が必要")
    return reasons


def match_candidates_for_position(
    pos: Position,
    employees: list[Employee],
    graph: dict,
    top_n: int = 10,
) -> tuple[list[MatchResult], list[tuple[str, str]]]:
    """ポジションに対する候補者リストと、除外された人の理由を返す。

    除外理由も返すのは監査要件。「なぜ推薦されなかったか」を
    後から説明できないシステムは人事では使えない。
    """
    results, excluded = [], []

    for emp in employees:
        ok, reason = hard_filter(emp, pos)
        if not ok:
            excluded.append((emp.emp_id, reason))
            continue

        r = score_pair(emp, pos, graph)
        if r is None:
            excluded.append((emp.emp_id, "必須スキル不足(ゲート)"))
            continue
        results.append(r)

    results.sort(key=lambda r: -r.total_score)
    return results[:top_n], excluded


def match_positions_for_employee(
    emp: Employee,
    positions: list[Position],
    graph: dict,
    top_n: int = 5,
) -> list[MatchResult]:
    """社員1名に対する異動先候補。本人向けフィードバックにも使える。"""
    results = []
    for pos in positions:
        ok, _ = hard_filter(emp, pos)
        if not ok:
            continue
        r = score_pair(emp, pos, graph)
        if r is not None:
            results.append(r)
    results.sort(key=lambda r: -r.total_score)
    return results[:top_n]
