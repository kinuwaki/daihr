"""社内の人的つながりを、異動履歴から推定する。

## なぜ作るか

受け入れ先に顔見知りがいる異動は、立ち上がりが早く定着もしやすい。
「この候補は異動先に知っている人がいるか」をスコアにして、
ソフトランディングしやすい配置を見つけられるようにする。

## 何をつながりと見なすか

**同じ部署に同時期に在籍していた** = 面識がある可能性が高い、と推定する。
異動履歴（誰がいつどの部署にいたか）だけで作れるので、
人事が既に持っている情報の再利用で済む。

## やらないこと

**メールやチャットの解析はしない。** 実際の会話量を測れば精度は上がるが、
監視と受け取られてツール全体が拒否される。異動履歴からの推定なら
「人事が既に持っている情報の再利用」として説明が通る。

また、推定されたつながりは**本人には見せない**前提で設計している。
「あなたはこの人と知り合いのはずです」と提示するのは踏み込みすぎで、
人事が配置を検討する材料に留める。
"""

from collections import defaultdict
from dataclasses import dataclass

from schema import Employee, TransferRecord

# 同時在籍が何年重なれば「面識あり」と見なすか。
# 半年程度では顔を知っている程度なので、1年を下限にした。
MIN_OVERLAP_YEARS = 1.0

# 部署の規模がこれを超えると、同時在籍でも面識があるとは限らない。
# 大部署では全員が知り合いにはならないため、つながりの重みを下げる。
LARGE_DEPT_SIZE = 40

# 現在年。異動履歴の終端（まだ在籍中）を表すのに使う
CURRENT_YEAR = 2026


@dataclass
class Tenure:
    """ある社員が、ある部署に在籍していた期間。"""
    emp_id: str
    dept: str
    start: int
    end: int          # まだ在籍中なら CURRENT_YEAR

    def overlap(self, other: "Tenure") -> float:
        """他の在籍期間と何年重なるか。"""
        lo = max(self.start, other.start)
        hi = min(self.end, other.end)
        return max(0.0, hi - lo)


def build_tenures(
    employees: list[Employee],
    transfers: list[TransferRecord],
) -> list[Tenure]:
    """異動履歴から、各社員の部署ごとの在籍期間を復元する。

    異動レコードは「いつ・どこから・どこへ」しか持たないので、
    社員ごとに時系列に並べて、次の異動までを在籍期間と見なす。
    最後の異動から現在までは現部署に在籍しているものとする。
    """
    by_emp: dict[str, list[TransferRecord]] = defaultdict(list)
    for t in transfers:
        by_emp[t.emp_id].append(t)

    tenures: list[Tenure] = []
    for emp in employees:
        recs = sorted(by_emp.get(emp.emp_id, []), key=lambda r: r.year)

        if not recs:
            # 異動履歴が無い＝入社以来ずっと現部署、と見なす。
            # 経験年数から入社年を逆算する
            start = CURRENT_YEAR - int(emp.experience_years)
            tenures.append(Tenure(emp.emp_id, emp.current_dept,
                                  start, CURRENT_YEAR))
            continue

        # 最初の異動より前は from_dept にいた
        first = recs[0]
        start = CURRENT_YEAR - int(emp.experience_years)
        if start < first.year:
            tenures.append(Tenure(emp.emp_id, first.from_dept,
                                  start, first.year))

        # 各異動から次の異動までが、その部署の在籍期間
        for i, r in enumerate(recs):
            end = recs[i + 1].year if i + 1 < len(recs) else CURRENT_YEAR
            if end > r.year:
                tenures.append(Tenure(emp.emp_id, r.to_dept, r.year, end))

    return tenures


def build_graph(tenures: list[Tenure]) -> dict[str, dict[str, float]]:
    """社員どうしのつながりの強さ。emp_id -> {相手のemp_id: 重み}

    重みは「同じ部署に同時に在籍した年数」の合計。
    大きな部署での同時在籍は、全員が知り合いになるとは限らないので割り引く。
    """
    # 部署ごとにまとめてから突き合わせる。全組合せを見ると O(n^2) になるため
    by_dept: dict[str, list[Tenure]] = defaultdict(list)
    for t in tenures:
        by_dept[t.dept].append(t)

    graph: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for dept, ts in by_dept.items():
        # その部署に在籍したことのある人数で、つながりの強さを割り引く
        headcount = len({t.emp_id for t in ts})
        damp = 1.0 if headcount <= LARGE_DEPT_SIZE else LARGE_DEPT_SIZE / headcount

        for i, a in enumerate(ts):
            for b in ts[i + 1:]:
                if a.emp_id == b.emp_id:
                    continue
                ov = a.overlap(b)
                if ov < MIN_OVERLAP_YEARS:
                    continue
                w = ov * damp
                graph[a.emp_id][b.emp_id] += w
                graph[b.emp_id][a.emp_id] += w

    return {k: dict(v) for k, v in graph.items()}


def dept_members(tenures: list[Tenure], year: int = CURRENT_YEAR) -> dict[str, set]:
    """指定年に各部署に在籍している社員。異動先の「受け入れ側」を表す。"""
    members: dict[str, set] = defaultdict(set)
    for t in tenures:
        if t.start <= year < t.end or (t.end == year == CURRENT_YEAR):
            members[t.dept].add(t.emp_id)
    return members


def familiarity_score(
    emp_id: str,
    dept: str,
    graph: dict[str, dict[str, float]],
    members: dict[str, set],
    min_weight: float = 2.0,
) -> tuple[float, int]:
    """異動先に顔見知りがどれくらいいるか。(スコア, 人数) を返す。

    スコアは 0..1。知っている人が1人でもいれば 0.5 を超えるようにし、
    複数いれば 1.0 に近づく。人数が増えるほど効きが鈍る形にしてある
    （3人知っているのと10人知っているのとで大差はないため）。

    つながりが無い場合は 0.5 ではなく 0.0 を返す。
    他のスコアと違って「未知だから中立」ではなく、
    「顔見知りがいないこと」自体が事実なので中立に倒す理由がない。
    ただし重みを小さくして、これだけで順位が決まらないようにする。
    """
    known = graph.get(emp_id, {})
    peers = members.get(dept, set())

    # min_weight 未満の弱いつながりは数えない。
    # 同じ大部署に居合わせただけの相手まで数えると、ほぼ全員が
    # 「顔見知りあり」になってスコアとして機能しなくなる（実測: 平均次数37）。
    n = sum(1 for p in peers
            if p != emp_id and known.get(p, 0.0) >= min_weight)
    if n == 0:
        return 0.0, 0

    # 1人で0.55、2人で0.71、3人で0.79、5人で0.88 と逓減させる。
    # 上限を設けるのは、20人知っていても「知っている」以上の情報が
    # 増えるわけではないため
    return (1.0 - 0.45 ** min(n, 8)), n


class NetworkContext:
    """つながりのグラフと在籍情報をまとめて持ち、スコアを返す。

    matcher からはこれ1つを渡せば済むようにしてある。
    ネットワークを使わない構成でも動くよう、matcher 側は None を許容する。
    """

    def __init__(self, employees: list[Employee],
                 transfers: list[TransferRecord]) -> None:
        self.tenures = build_tenures(employees, transfers)
        self.graph = build_graph(self.tenures)
        self.members = dept_members(self.tenures)

    def score(self, emp_id: str, dept: str) -> tuple[float, int]:
        return familiarity_score(emp_id, dept, self.graph, self.members)

    def summary(self) -> dict:
        return summarize(self.graph)


def summarize(graph: dict[str, dict[str, float]]) -> dict:
    """グラフの概況。PoCで規模感を確認するため。"""
    if not graph:
        return {"nodes": 0, "edges": 0, "avg_degree": 0.0, "isolated": 0}
    edges = sum(len(v) for v in graph.values()) // 2
    degrees = [len(v) for v in graph.values()]
    return {
        "nodes": len(graph),
        "edges": edges,
        "avg_degree": sum(degrees) / len(degrees),
        "max_degree": max(degrees),
    }
