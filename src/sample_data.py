"""PoC用のダミーデータ生成。

## 組織構造について

部署・職種の構成は Daigasグループ（大阪ガス）の**公開情報**を土台にしている。
公式サイト・有価証券報告書・統合報告書から取れる組織構造だけを使っており、
社員データそのものは**すべて架空**（乱数生成）である。実データは含まない。

出典:
  - Daigasグループ 新機構表（2026年4月1日付）
    https://www.osakagas.co.jp/company/press/pr2026/1798913_60968.html
  - 有価証券報告書 第208期（2026年3月期）
  - Daigasグループ 人的資本レポート2025

実データに差し替えるときは generate() を置き換える。
スキーマ（schema.py）は実データの項目名に合わせて調整すること。

## 意図的に入れてある偏り

異動履歴に属性による偏りを入れてある。公平性検査が機能することを
確認するためで、これが無いと検査のテストができない。
"""

import random

from schema import Employee, Position, TransferRecord

# ---------------------------------------------------------------- 組織

# 事業セグメント（有報 第208期の3区分）
SEGMENTS = {
    "国内エネルギー": ["ガス製造・エンジニアリング", "電力", "エナジーソリューション",
                       "ネットワーク"],
    "海外エネルギー": ["資源・海外"],
    "ライフ&ビジネスソリューション": ["都市開発", "情報システム", "ケミカル"],
    "コーポレート": ["経営企画", "事業創造", "DX企画", "人事", "財務", "資材"],
}

# 事業所（勤務地の単位）。
#
# 大阪ガスネットワークの5事業部は、公式サイトのHTMLを直接取得して
# 逐語確認した。ここだけが一次情報で裏取りできた下位組織である。
#   https://network.osakagas.co.jp/company/location.html
#
# 各社の課・室・チームレベルの組織名は、組織図が「テキストを含まない画像」で
# 公開されているため通常のWeb取得では読めず、本調査では確認できなかった。
# 確認できないものを書くと実在企業について誤った情報を残すことになるので、
# 推測で埋めていない。実データに差し替えるときに社内の正式名称を入れること。
NETWORK_BRANCHES = ["大阪事業部", "南部事業部", "北東部事業部",
                    "兵庫事業部", "京滋事業部"]

# 部署 -> 所属セグメント（逆引き）
DEPT_SEGMENT = {d: seg for seg, ds in SEGMENTS.items() for d in ds}
DEPTS = list(DEPT_SEGMENT)

# セグメント別の配属比率。有報 第208期の従業員数
# （国内エネルギー 11,039 / 海外エネルギー 333 / LBS 10,463、計 21,835）に
# おおむね合わせている。コーポレートは有報上は独立集計されていないため、
# 国内エネルギーとLBSから按分した仮置き。
#
# 部署数で均等割りすると部署の多いコーポレートが最大勢力になってしまい、
# 「少人数部署への異動」という現実的な状況が再現できない。
SEGMENT_WEIGHT = {
    "国内エネルギー": 0.46,
    "海外エネルギー": 0.02,
    "ライフ&ビジネスソリューション": 0.42,
    "コーポレート": 0.10,
}

# 業務分野別のスキル。
# Daigasのタレントマネジメントは業務分野を18領域に分類しているとされるが、
# 領域の詳細は非公開のため、ここは事業内容から推定した仮置き。
# 実運用では社内の分類に差し替えること。
SKILL_POOL = {
    "ガス製造・エンジニアリング": [
        "プラント設計", "設備保全", "保安管理", "LNG基地運用", "工程改善"],
    "電力": [
        "発電所運用", "電力需給管理", "電力市場取引", "再エネ開発", "系統技術"],
    "エナジーソリューション": [
        "法人営業", "エネルギーコンサル", "省エネ提案", "料金設計", "顧客折衝"],
    "ネットワーク": [
        "導管技術", "保安管理", "工事管理", "設備投資計画", "災害対応"],
    "資源・海外": [
        "資源開発", "国際契約", "英語", "海外プロジェクト管理", "為替リスク管理"],
    "都市開発": [
        "不動産開発", "賃貸運営", "用地取得", "建築知識", "投資評価"],
    "情報システム": [
        "システム設計", "データ分析", "Python", "SQL", "情報セキュリティ",
        "クラウド基盤"],
    "ケミカル": [
        "材料開発", "品質管理", "生産技術", "特許実務", "化学分析"],
    "経営企画": [
        "経営分析", "事業計画", "M&A実務", "投資評価", "サステナビリティ"],
    "事業創造": [
        "新規事業開発", "技術調査", "スタートアップ連携", "事業性評価",
        "カーボンニュートラル"],
    "DX企画": [
        "DX推進", "データ分析", "業務改革", "システム企画", "Python"],
    "人事": [
        "採用", "労務管理", "人材開発", "人事制度設計", "ダイバーシティ推進"],
    "財務": [
        "財務会計", "管理会計", "資金調達", "税務", "投資評価"],
    "資材": [
        "調達戦略", "契約実務", "サプライヤ管理", "コスト分析"],
}

# 人事評価のコンピテンシー項目。総合評価点は持たない（項目別のみ使う）
COMPETENCIES = ["課題発見力", "対人調整力", "計数感覚", "実行推進力",
                "後進育成", "変化対応力", "安全意識"]

# 部署が求めるコンピテンシーの傾向
DEPT_COMPETENCIES = {
    "ガス製造・エンジニアリング": ["安全意識", "実行推進力"],
    "電力":                     ["計数感覚", "変化対応力"],
    "エナジーソリューション":     ["対人調整力", "実行推進力"],
    "ネットワーク":              ["安全意識", "実行推進力"],
    "資源・海外":                ["変化対応力", "課題発見力"],
    "都市開発":                  ["計数感覚", "対人調整力"],
    "情報システム":              ["課題発見力", "変化対応力"],
    "ケミカル":                  ["課題発見力", "安全意識"],
    "経営企画":                  ["課題発見力", "計数感覚"],
    "事業創造":                  ["課題発見力", "変化対応力"],
    "DX企画":                   ["変化対応力", "課題発見力"],
    "人事":                     ["対人調整力", "後進育成"],
    "財務":                     ["計数感覚", "実行推進力"],
    "資材":                     ["計数感覚", "対人調整力"],
}

CERTS = ["簿記2級", "TOEIC800", "情報処理安全確保支援士", "中小企業診断士",
         "社会保険労務士", "PMP", "統計検定2級", "高圧ガス製造保安責任者",
         "エネルギー管理士", "電気主任技術者", "宅地建物取引士"]

# 部署固有の必須資格（保安系は法令で有資格者が必要）
DEPT_REQUIRED_CERTS = {
    "ガス製造・エンジニアリング": ["高圧ガス製造保安責任者"],
    "ネットワーク": ["高圧ガス製造保安責任者"],
    "電力": ["電気主任技術者"],
    "都市開発": ["宅地建物取引士"],
}

WISHES = [
    "データを活用した業務改善に携わりたい",
    "海外事業に関わりたい",
    "マネジメント経験を積みたい",
    "専門性を深めたい",
    "新しい部門で幅を広げたい",
    "顧客に近い仕事がしたい",
    "企画・戦略の仕事に挑戦したい",
    "カーボンニュートラルに関わりたい",
]

LOCATIONS = ["大阪", "東京", "京都", "神戸", "海外"]

ROLES = ["担当", "主任", "係長", "課長"]


def generate(n_employees: int = 240, n_positions: int = 24, seed: int = 42):
    """架空の社員・ポジション・異動履歴を生成する。

    n_employees は実際の連結従業員数（約21,800人）よりはるかに小さい。
    PoCで挙動を確認するための規模で、公平性検査の標本サイズの
    問題を再現できる程度にしてある。
    """
    rng = random.Random(seed)

    def pick_dept() -> str:
        """セグメントの従業員数比に沿って部署を選ぶ。"""
        seg = rng.choices(list(SEGMENT_WEIGHT),
                          weights=list(SEGMENT_WEIGHT.values()))[0]
        return rng.choice(SEGMENTS[seg])

    employees: list[Employee] = []
    for i in range(n_employees):
        dept = pick_dept()

        # 自部署スキルを厚めに持たせる
        skills: dict[str, int] = {}
        pool = SKILL_POOL[dept]
        for s in rng.sample(pool, k=min(len(pool), rng.randint(3, 5))):
            skills[s] = rng.randint(2, 5)

        # 他部署スキルも一定数持たせる。異動候補になる人は
        # 過去の経験や兼務で隣接領域のスキルを持っていることが多い
        for other in rng.sample([d for d in DEPTS if d != dept],
                                k=rng.randint(1, 3)):
            op = SKILL_POOL[other]
            for s in rng.sample(op, k=min(len(op), rng.randint(1, 3))):
                skills[s] = rng.randint(2, 4)

        # 過去所属部署のスキルは強く残っているものとする
        prior = rng.sample([d for d in DEPTS if d != dept], k=rng.randint(0, 2))
        for d in prior:
            dp = SKILL_POOL[d]
            for s in rng.sample(dp, k=min(len(dp), rng.randint(1, 2))):
                skills[s] = max(skills.get(s, 0), rng.randint(3, 5))

        employees.append(Employee(
            emp_id=f"E{i:04d}",
            name=f"社員{i:04d}",
            current_dept=dept,
            current_role=rng.choice(ROLES),
            grade=rng.randint(1, 6),
            location=rng.choice(LOCATIONS),
            experience_years=round(rng.uniform(1, 30), 1),
            skills=skills,
            certifications=rng.sample(CERTS, k=rng.randint(0, 3)),
            career_wish=rng.choice(WISHES) if rng.random() < 0.7 else "",
            past_depts=prior,
            mobility_ok=rng.random() < 0.85,
            # 全員が全項目の評価を持つとは限らない（異動直後など）
            competencies={c: rng.randint(2, 5)
                          for c in rng.sample(COMPETENCIES,
                                              k=rng.randint(3, len(COMPETENCIES)))},
            eval_consent=rng.random() < 0.9,
            gender=rng.choice(["男性", "女性"]),
            age_band=rng.choice(["20代", "30代", "40代", "50代"]),
        ))

    positions: list[Position] = []
    for i in range(n_positions):
        dept = pick_dept()
        pool = SKILL_POOL[dept]
        req = {s: rng.randint(3, 4) for s in rng.sample(pool, k=2)}
        rest = [x for x in pool if x not in req]
        pref = {s: rng.randint(2, 3)
                for s in rng.sample(rest, k=min(len(rest), rng.randint(1, 2)))}
        gmin = rng.randint(1, 4)

        # 保安系の部署は法令上の有資格者が必要。
        # ここでランダムに資格を割り当てると「ケミカル部門が電気主任技術者を
        # 必須にする」ような無意味な要件ができてしまうので、
        # 部署に紐づく資格だけを使う。
        certs = list(DEPT_REQUIRED_CERTS.get(dept, []))

        positions.append(Position(
            pos_id=f"P{i:03d}",
            dept=dept,
            title=f"{dept}{rng.choice(['担当', '主任', '企画担当', 'リーダー'])}",
            location=rng.choice(LOCATIONS),
            grade_min=gmin,
            grade_max=min(6, gmin + rng.randint(1, 2)),
            required_skills=req,
            preferred_skills=pref,
            required_competencies={
                c: rng.randint(3, 4)
                for c in rng.sample(DEPT_COMPETENCIES[dept],
                                    k=rng.randint(1, 2))
            },
            required_certifications=certs,
            description=f"{DEPT_SEGMENT[dept]}セグメントの{dept}部門における"
                        f"実務および改善推進を担当する。",
            headcount=rng.randint(1, 3),
        ))

    # 異動履歴。意図的に偏りを入れる（過去の慣行の偏りを再現）
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
    print(f"部署 {len(DEPTS)} / セグメント {len(SEGMENTS)}")
    print()
    for seg, ds in SEGMENTS.items():
        n = sum(1 for e in emps if DEPT_SEGMENT[e.current_dept] == seg)
        print(f"  {seg}: {n}名  ({'、'.join(ds)})")
    print()
    print("--- 社員サンプル ---")
    print(emps[0].feature_text())
    print()
    print("--- ポジションサンプル ---")
    print(poss[0].feature_text())
