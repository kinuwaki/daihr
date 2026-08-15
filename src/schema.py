"""異動支援AIのデータスキーマ定義。

設計方針: 保護属性（性別・年齢・国籍など）は Employee に持たせるが、
マッチングの特徴量には絶対に流さない。公平性検査でのみ参照する。
そのため FEATURE_FIELDS と AUDIT_ONLY_FIELDS を明示的に分離している。
"""

from dataclasses import dataclass, field


# マッチングの特徴量として使ってよいフィールド
FEATURE_FIELDS = frozenset({
    "skills", "experience_years", "current_dept", "current_role",
    "grade", "location", "certifications", "career_wish", "past_depts",
    "competencies",
})

# 公平性監査でのみ参照。モデル入力に混ぜてはいけない
AUDIT_ONLY_FIELDS = frozenset({"gender", "age_band", "nationality", "tenure_band"})


@dataclass
class Employee:
    emp_id: str
    name: str
    current_dept: str
    current_role: str
    grade: int                      # 等級。1が最も下位
    location: str
    experience_years: float
    skills: dict[str, int]          # スキル名 -> 習熟度 1..5

    # 人事評価のうち、コンピテンシー別の評価。項目名 -> 評価 1..5
    # 例: {"課題発見力": 4, "対人調整力": 3, "計数感覚": 5}
    #
    # 総合評価点は持たせない。総合点でのランキングは異動支援ではなく選別になり、
    # また「なぜ推薦されなかったか」の説明が本人開示請求時に極めて難しくなる。
    # 職務適合に直接関係する項目別の評価だけを使う。
    competencies: dict[str, int] = field(default_factory=dict)

    # 評価データの利用同意。取れていない社員はコンピテンシーを参照しない
    eval_consent: bool = True

    certifications: list[str] = field(default_factory=list)
    career_wish: str = ""           # 自己申告のキャリア希望（自由記述）
    past_depts: list[str] = field(default_factory=list)
    mobility_ok: bool = True        # 異動可否フラグ（本人同意・制約）

    # --- 以下は監査専用。特徴量に使わない ---
    gender: str = ""
    age_band: str = ""

    def usable_competencies(self) -> dict[str, int]:
        """参照してよいコンピテンシー評価。同意が無ければ空を返す。

        評価は処遇決定のために集めたデータなので、異動推薦への利用には
        本人同意を前提にする。同意が無い社員は評価を使わずに評価される
        （スキルと本人希望だけで候補になれる）。
        """
        return self.competencies if self.eval_consent else {}

    def feature_text(self) -> str:
        """埋め込み用のテキスト表現。保護属性は一切含めない。"""
        skill_str = "、".join(
            f"{name}(習熟度{lv})" for name, lv in sorted(
                self.skills.items(), key=lambda kv: -kv[1]
            )
        )
        parts = [
            f"現職: {self.current_dept} {self.current_role}",
            f"経験年数: {self.experience_years}年",
            f"スキル: {skill_str}",
        ]
        if (comp := self.usable_competencies()):
            parts.append("コンピテンシー: " + "、".join(
                f"{n}({v})" for n, v in sorted(comp.items(), key=lambda kv: -kv[1])
            ))
        if self.certifications:
            parts.append(f"資格: {'、'.join(self.certifications)}")
        if self.past_depts:
            parts.append(f"過去所属: {'、'.join(self.past_depts)}")
        if self.career_wish:
            parts.append(f"キャリア希望: {self.career_wish}")
        return " / ".join(parts)


@dataclass
class Position:
    pos_id: str
    dept: str
    title: str
    location: str
    grade_min: int
    grade_max: int
    required_skills: dict[str, int]   # スキル名 -> 必要習熟度
    preferred_skills: dict[str, int] = field(default_factory=dict)

    # このポジションで求められるコンピテンシー。項目名 -> 必要水準 1..5
    # スキル（何ができるか）とは別軸で、行動特性の適合を見る。
    required_competencies: dict[str, int] = field(default_factory=dict)

    required_certifications: list[str] = field(default_factory=list)
    description: str = ""
    headcount: int = 1

    def feature_text(self) -> str:
        req = "、".join(f"{n}(要{lv})" for n, lv in self.required_skills.items())
        pref = "、".join(f"{n}(歓迎{lv})" for n, lv in self.preferred_skills.items())
        parts = [f"部署: {self.dept}", f"職位: {self.title}", f"必須スキル: {req}"]
        if pref:
            parts.append(f"歓迎スキル: {pref}")
        if self.required_competencies:
            parts.append("求めるコンピテンシー: " + "、".join(
                f"{n}(要{v})" for n, v in self.required_competencies.items()))
        if self.description:
            parts.append(self.description)
        return " / ".join(parts)


@dataclass
class TransferRecord:
    """過去の異動実績。協調フィルタリングのシグナル源。"""
    emp_id: str
    from_dept: str
    to_dept: str
    year: int
    from_role: str = ""
    to_role: str = ""
