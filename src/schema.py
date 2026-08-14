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
    certifications: list[str] = field(default_factory=list)
    career_wish: str = ""           # 自己申告のキャリア希望（自由記述）
    past_depts: list[str] = field(default_factory=list)
    mobility_ok: bool = True        # 異動可否フラグ（本人同意・制約）

    # --- 以下は監査専用。特徴量に使わない ---
    gender: str = ""
    age_band: str = ""

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
    required_certifications: list[str] = field(default_factory=list)
    description: str = ""
    headcount: int = 1

    def feature_text(self) -> str:
        req = "、".join(f"{n}(要{lv})" for n, lv in self.required_skills.items())
        pref = "、".join(f"{n}(歓迎{lv})" for n, lv in self.preferred_skills.items())
        parts = [f"部署: {self.dept}", f"職位: {self.title}", f"必須スキル: {req}"]
        if pref:
            parts.append(f"歓迎スキル: {pref}")
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
