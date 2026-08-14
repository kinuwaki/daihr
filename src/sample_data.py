"""PoC用のダミーデータ生成。

実データを触る前にパイプライン全体を通すためのもの。
意図的に「異動履歴に偏りがある」データを作ってあるので、
公平性チェックが機能することも確認できる。
"""

import random

from schema import Employee, Position, TransferRecord

SKILL_POOL = {
    "営業": ["法人営業", "提案書作成", "顧客折衝", "与信管理", "CRM運用"],
    "マーケティング": ["市場調査", "デジタル広告", "SEO", "データ分析", "ブランド戦略"],
    "情報システム": ["Python", "SQL", "ネットワーク", "情報セキュリティ", "クラウド基盤"],
    "経理": ["財務会計", "管理会計", "税務", "Excel", "決算業務"],
    "人事": ["採用", "労務管理", "人材開発", "人事制度設計", "データ分析"],
    "製造": ["生産管理", "品質管理", "工程改善", "安全管理", "原価管理"],
}

CERTS = ["簿記2級", "TOEIC800", "情報処理安全確保支援士", "中小企業診断士",
         "社会保険労務士", "PMP", "統計検定2級"]

WISHES = [
    "データを活用した業務改善に携わりたい",
    "海外事業に関わりたい",
    "マネジメント経験を積みたい",
    "専門性を深めたい",
    "新しい部門で幅を広げたい",
    "顧客に近い仕事がしたい",
    "企画・戦略の仕事に挑戦したい",
]

LOCATIONS = ["東京", "大阪", "名古屋", "福岡"]


def generate(n_employees: int = 120, n_positions: int = 15, seed: int = 42):
    rng = random.Random(seed)
    depts = list(SKILL_POOL.keys())

    employees: list[Employee] = []
    for i in range(n_employees):
        dept = rng.choice(depts)
        # 自部署スキルを厚めに持たせる
        skills: dict[str, int] = {}
        for s in rng.sample(SKILL_POOL[dept], k=rng.randint(3, 5)):
            skills[s] = rng.randint(2, 5)

        # 他部署スキルも一定数持たせる。実際の会社では、異動候補になる人は
        # 過去の経験や兼務で隣接領域のスキルを持っていることが多い。
        # ここを弱くしすぎると「異動可能な候補が誰もいない」データになる。
        for other in rng.sample([d for d in depts if d != dept],
                                k=rng.randint(1, 3)):
            for s in rng.sample(SKILL_POOL[other], k=rng.randint(1, 3)):
                skills[s] = rng.randint(2, 4)

        # 過去所属部署のスキルは特に強く残っているものとする
        prior = rng.sample([d for d in depts if d != dept], k=rng.randint(0, 2))
        for d in prior:
            for s in rng.sample(SKILL_POOL[d], k=rng.randint(1, 2)):
                skills[s] = max(skills.get(s, 0), rng.randint(3, 5))

        grade = rng.randint(1, 6)
        employees.append(Employee(
            emp_id=f"E{i:04d}",
            name=f"社員{i:04d}",
            current_dept=dept,
            current_role=rng.choice(["担当", "主任", "係長", "課長"]),
            grade=grade,
            location=rng.choice(LOCATIONS),
            experience_years=round(rng.uniform(1, 25), 1),
            skills=skills,
            certifications=rng.sample(CERTS, k=rng.randint(0, 2)),
            career_wish=rng.choice(WISHES) if rng.random() < 0.7 else "",
            past_depts=prior,
            mobility_ok=rng.random() < 0.85,
            gender=rng.choice(["男性", "女性"]),
            age_band=rng.choice(["20代", "30代", "40代", "50代"]),
        ))

    positions: list[Position] = []
    for i in range(n_positions):
        dept = rng.choice(depts)
        pool = SKILL_POOL[dept]
        req = {s: rng.randint(3, 4) for s in rng.sample(pool, k=2)}
        pref = {s: rng.randint(2, 3)
                for s in rng.sample([x for x in pool if x not in req],
                                    k=rng.randint(1, 2))}
        gmin = rng.randint(1, 4)
        positions.append(Position(
            pos_id=f"P{i:03d}",
            dept=dept,
            title=f"{dept}{rng.choice(['担当', '主任', '企画担当', 'リーダー'])}",
            location=rng.choice(LOCATIONS),
            grade_min=gmin,
            grade_max=min(6, gmin + rng.randint(1, 2)),
            required_skills=req,
            preferred_skills=pref,
            required_certifications=(
                rng.sample(CERTS, k=1) if rng.random() < 0.25 else []
            ),
            description=f"{dept}部門における実務および改善推進を担当する。",
            headcount=rng.randint(1, 3),
        ))

    # 異動履歴。意図的に偏りを入れる（特定属性が異動しにくい過去を再現）
    transfers: list[TransferRecord] = []
    for emp in employees:
        if not emp.past_depts:
            continue
        bias = 0.75 if emp.gender == "男性" else 0.45
        if rng.random() > bias:
            continue
        for j, prev in enumerate(emp.past_depts):
            transfers.append(TransferRecord(
                emp_id=emp.emp_id,
                from_dept=prev,
                to_dept=(emp.past_depts[j + 1]
                         if j + 1 < len(emp.past_depts) else emp.current_dept),
                year=2026 - rng.randint(1, 8),
            ))

    return employees, positions, transfers


if __name__ == "__main__":
    emps, poss, trs = generate()
    print(f"社員 {len(emps)}名 / ポジション {len(poss)}件 / 異動履歴 {len(trs)}件")
    print()
    print("--- 社員サンプル ---")
    print(emps[0].feature_text())
    print()
    print("--- ポジションサンプル ---")
    print(poss[0].feature_text())
