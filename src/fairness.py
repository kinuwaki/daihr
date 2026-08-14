"""公平性チェック。

推薦結果が保護属性によって偏っていないかを検査する。
AI Fairness 360 / Fairlearn を入れる前段として、
依存なしで動く最小実装を置いてある（PoCで真っ先に回すべき検査）。

## なぜ比率だけでは駄目か

Demographic Parity Ratio（属性群ごとの推薦率の比、4/5ルール）だけで判定すると、
小標本では**実体のない偏りを検出してしまう**。

実際にこのPoCで、年代と実力が完全に無相関なダミーデータを使っても
parity ratio が seed によって 0.20〜0.78 まで暴れることを確認した。
これを「要調査」と報告し続けると、担当者は警告を無視するようになり、
本物のバイアスを見逃す。

そのため本モジュールは比率に加えて**統計的有意性**を必ず併記する。
判定は次の2条件の AND:
  1. parity ratio < 0.8      （実務上の影響が大きい）
  2. p値 < 0.05              （偶然では説明しにくい）

p値の計算には Fisher の正確確率検定（2×2）を用いる。
小標本でも使え、外部依存が不要なため。
"""

from collections import defaultdict
from math import lgamma, exp

from schema import Employee, AUDIT_ONLY_FIELDS

THRESHOLD = 0.8       # 4/5ルール
ALPHA = 0.05          # 有意水準
MIN_GROUP_SIZE = 20   # これ未満の群は判定を保留し、データ蓄積を促す


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2分割表に対する Fisher の正確確率検定（両側）のp値。

        群1: 推薦 a / 非推薦 b
        群2: 推薦 c / 非推薦 d

    観測された表以下の確率を持つ全ての表の確率を合計する標準的な定義。
    """
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, col1 = a + b, a + c

    def prob(x: int) -> float:
        lp = (_log_comb(row1, x) + _log_comb(n - row1, col1 - x)
              - _log_comb(n, col1))
        return exp(lp) if lp != float("-inf") else 0.0

    observed = prob(a)
    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    # 浮動小数の誤差で観測表自身が漏れないよう僅かな許容を置く
    total = sum(p for x in range(lo, hi + 1)
                if (p := prob(x)) <= observed * (1 + 1e-9))
    return min(1.0, total)


def demographic_parity(
    all_employees: list[Employee],
    recommended_ids: set[str],
    attribute: str,
) -> dict:
    """属性値ごとの推薦率、比率、および有意性を返す。"""
    if attribute not in AUDIT_ONLY_FIELDS:
        raise ValueError(
            f"{attribute} は監査対象属性ではありません。"
            f"監査可能: {sorted(AUDIT_ONLY_FIELDS)}"
        )

    totals: dict[str, int] = defaultdict(int)
    picked: dict[str, int] = defaultdict(int)

    for emp in all_employees:
        val = getattr(emp, attribute, "")
        if not val:
            continue
        totals[val] += 1
        if emp.emp_id in recommended_ids:
            picked[val] += 1

    if not totals:
        return {"attribute": attribute, "rates": {}, "counts": {},
                "ratio": None, "p_value": None, "verdict": "データなし",
                "pass": True}

    rates = {v: picked[v] / totals[v] for v in totals}
    max_rate = max(rates.values())
    ratio = (min(rates.values()) / max_rate) if max_rate > 0 else None

    # 最も推薦率が高い群と低い群を比較して有意性を判定する。
    #
    # 注意: 「最大と最小」を事後的に選ぶこと自体が多重比較にあたる。
    # 群がk個あればkC2通りの対比較から最も極端なものを拾っているので、
    # 素のp値は楽観的に出る。Bonferroni補正で対比較数を掛けて補正する。
    # （無相関データで偽陽性率15%→ほぼ0%になることを確認済み）
    best = max(rates, key=lambda v: rates[v])
    worst = min(rates, key=lambda v: rates[v])
    k = len(rates)
    n_comparisons = max(1, k * (k - 1) // 2)
    raw_p = fisher_exact_two_sided(
        picked[best], totals[best] - picked[best],
        picked[worst], totals[worst] - picked[worst],
    ) if best != worst else 1.0
    p_value = min(1.0, raw_p * n_comparisons)

    small = min(totals.values()) < MIN_GROUP_SIZE

    if ratio is None or ratio >= THRESHOLD:
        verdict, ok = "OK", True
    elif small:
        verdict, ok = "判定保留(標本不足)", True
    elif p_value < ALPHA:
        verdict, ok = "要調査", False
    else:
        verdict, ok = "偏りあり(有意でない)", True

    return {
        "attribute": attribute,
        "counts": {v: (picked[v], totals[v]) for v in totals},
        "rates": rates,
        "ratio": ratio,
        "p_value": p_value,
        "compared": (best, worst),
        "small_sample": small,
        "verdict": verdict,
        "pass": ok,
    }


def audit(all_employees: list[Employee], recommended_ids: set[str]) -> list[dict]:
    """全監査属性についてチェックを実行。"""
    return [
        demographic_parity(all_employees, recommended_ids, attr)
        for attr in sorted(AUDIT_ONLY_FIELDS)
        if any(getattr(e, attr, "") for e in all_employees)
    ]


def format_report(reports: list[dict]) -> str:
    lines = []
    for rep in reports:
        ratio = rep["ratio"]
        ratio_str = f"{ratio:.2f}" if ratio is not None else "N/A"
        p = rep["p_value"]
        p_str = f"{p:.3f}" if p is not None else "N/A"
        lines.append(
            f"[{rep['verdict']}] {rep['attribute']}  "
            f"parity ratio = {ratio_str}  p = {p_str}"
        )
        for val, rate in sorted(rep["rates"].items(), key=lambda kv: -kv[1]):
            pk, tot = rep["counts"][val]
            flag = " *" if tot < MIN_GROUP_SIZE else ""
            lines.append(f"    {val:<8} {pk:>3}/{tot:<3} ({rate:5.1%}) "
                         f"{'#' * int(rate * 30)}{flag}")

        if rep["verdict"] == "要調査":
            lines.append(
                "    → 統計的に有意な偏りです。特徴量に代理変数が"
                "混入していないか確認してください。"
            )
        elif rep["verdict"] == "偏りあり(有意でない)":
            lines.append(
                f"    → 比率は{THRESHOLD}を下回りますが、p={p_str}で"
                "偶然の範囲内です。標本を増やして再検査してください。"
            )
        elif rep["verdict"] == "判定保留(標本不足)":
            lines.append(
                f"    → *印の群が{MIN_GROUP_SIZE}名未満です。"
                "この規模では偏りの有無を判断できません。"
            )
        lines.append("")
    return "\n".join(lines)
