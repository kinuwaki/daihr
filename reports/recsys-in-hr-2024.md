# RecSys in HR 2024 — 全論文サーベイ

**The 4th Workshop on Recommender Systems for Human Resources**
ACM RecSys 2024 併設 ／ 2024年10月14〜18日 ／ バーリ（イタリア）

論文集: https://ceur-ws.org/Vol-3788/ （**全文無料公開**）

全10本のPDFを取得し、本文を読んで要約しています。
記載した数値はすべて論文本文からの引用です。

---

## この回を一言でいうと

**「評価が信用できない」年**でした。3本が独立に、
**いま使われている評価指標・ベンチマーク・説明UIが機能していない**ことを示しています。

手法の改善より、**その改善を正しく測れているのかという問い**が中心にありました。

---

## 実務者が最初に読むべき3本

### 1. オフライン指標の改善が、オンラインの成果につながらない（Indeed）

> **Pseudo-online Measurement of Retrieval Recall for Job Recommendations
> — A case study at Indeed**
> Liyasi Wu, Yi Wei Pang, Warren Cai（**Indeed.com**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_6.pdf

**問題意識（本文より）**:
> NDCG、recall@k、precision@k といったオフライン指標の改善が、
> クリック率・コンバージョン率といった一般的なオンライン指標の向上に
> つながらないという観察がある。**特に推薦システムの初期段階で顕著**。

Indeed の推薦は多段階（**retrieval → filtering → scoring → ordering**）で、
段階が進むほど件数は減り、質は上がるはずの構造です。

**核心的な指摘**: **retrieval 段で改善しても、最終段のランキングモデルの偏りに
打ち消される**。ビジネス指標は最終ランキングに強く影響されるため、
中間段階の良し悪しが見えない。

**対処**: retrieval 段の有効性だけを測る **pseudo-online recall@k** を設計した。

**社内異動への含意**: 「候補の絞り込みを改善した」と「担当者が良い異動を決めた」は
別物です。**どの段階を測っているのかを意識しないと、改善が改善に見えません。**

---

### 2. 社内の専門家発見システムは、評価そのものが歪んでいる

> **On the Biased Assessment of Expert Finding Systems**
> Jens-Joris Decorte, Jeroen Van Hautte, Chris Develder, Thomas Demeester
> （Ghent University – imec / **TechWolf**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_10.pdf

**この論文が社内異動に最も近い**。冒頭でこう位置づけています。

> 大きな組織では、チームや部門に散らばった内部知識を活用するために、
> **特定のトピックに詳しい人（専門家）を見つけることが重要**である。

**何を発見したか**:

専門家発見システムの評価には「誰が何の専門家か」の正解データが要りますが、
これを人手で網羅的に作るのは困難です。そのため実務では
**システムが推薦した知識領域を人が検証する**形で正解を作ります。

ところがこの作り方が評価を歪めます。

- **システムが検証した注釈は、従来型の用語ベース検索の性能を過大評価させる**
- その結果、**新しいニューラル手法との比較が無効になる**
- 知識領域に同義語を追加すると、**構成語の字面が一致するものへの強い偏り**が露呈する

論文は注釈プロセスへの制約を提案し、それでも有用な注釈候補は出せることを示しています。

**社内異動への含意**: 社内で「この人はこのスキルを持つ」という正解データを
作るとき、**ツールが出した候補を人が承認する形にすると、ツールに都合の良い
正解ができあがります**。自社で精度を測るときの落とし穴として、
知っておく価値があります。

---

### 3. 説明の効果を測ったら、有意差が出なかった

> **Creating Healthy Friction: Determining Stakeholder Requirements of
> Job Recommendation Explanations**
> Roan Schellingerhout, Francesco Barile, Nava Tintarev（Maastricht University）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_7.pdf ／ https://arxiv.org/abs/2409.15971

**何をしたか**: 事前登録済みの混合デザインによる課題ベースのユーザ実験（**n=30**）。
候補者・リクルーター・企業担当者の**3種類の利害関係者**が、
モデルの説明にもとづいて実際に意思決定を行った。

**わかったこと（本文より）**:
> 本物の説明は、意思決定の速度と精度を**有意には改善しなかった**
> （non-significant trend にとどまる）

信頼・有用性・透明性についても、本物の説明が上回る傾向はあったものの
**統計的に有意ではありません**。

**結論**: 説明を「説得の道具」ではなく、
**健全な摩擦（healthy friction）を生む意思決定支援**として位置づけ直すべき。

**2025年には、より大規模な実験（人事管理職410名）が同じ方向の結果**を出しています
（[2025年版サーベイ](recsys-in-hr-2025.md)参照）。
**2年連続で、規模の異なる2つの実験が「説明を出せば済む」を否定している**点が重要です。

---

## 実務システムの知見

### モデル更新時の「集団の安定性」を監視する（Indeed）

> **Enhancing Reliability in Recommendation Systems: Beyond point estimations
> to monitor population stability**
> Yingshi Chen, Mohit Jain, Vaibhav Sawhney, Liyasi Wu（**Indeed Inc.**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_5.pdf

モデルを再学習・改良するたびに、予測の一貫性が保たれるかを監視する必要があります。
Indeed は従来「点推定」で見ていましたが、それでは不十分でした。

**提案**: **CPSI（Cumulative Probability Stability Index）**。
PSI（Probability Stability Index）から派生した指標で、
**予測分布の安定性**を監視する。

論文は、モデル移行時の**重大な不安定性を検出できた**と報告しています。

**社内異動への含意**: 一度作って終わりではなく、**モデルを更新したときに
推薦の傾向が変わっていないかを監視する仕組み**が要る、という実務的な指摘です。
人事の場合、去年と今年で推薦傾向が変わると説明できません。

---

### 大規模な相互マッチングを現実的な計算量にする（日本発）

> **Parallel and Mini-Batch Stable Matching for Large-Scale Reciprocal
> Recommender Systems**
> 中田健人（**Sony Network Communications**）、川村和樹（**東京大学**）、
> 古川亮介（Sony Network Communications）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_4.pdf

**問題意識**: 求人や婚活のような**両側マッチング**では、双方の選好を考慮する
必要があります。推薦が一部の人に集中すると、**マッチ機会が損なわれ、
総マッチ数が減る**。

**手法**: 譲渡可能効用をもつ安定マッチング理論を適用。ただし計算量とメモリが
利用者数の**2乗**で増えるため大規模化が困難でした。
**Sinkhorn アルゴリズムの並列化とミニバッチ化**でこれを解決。

**結果**: **GPU 1枚で最大100万サンプルを処理可能**。マッチ数を落とさずに。

**社内異動への含意**: 社内異動も**本人・受入部署の双方の選好**がある両側マッチングです。
「候補者を並べる」だけでなく「全体として何組成立させるか」を最適化する視点は、
人事異動の一括調整（玉突き人事）と相性が良い考え方です。

---

## スキル体系・スキル抽出

### 国家規模の動的な職業・スキル知識グラフ（シンガポール政府）

> **A Dynamic Jobs-Skills Knowledge Graph**
> Alejandro Seif（**GovTech Singapore**）、Sarah Toh（**SkillsFuture Singapore**）、
> Hwee Kuan Lee（**A*STAR**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_1.pdf

**問題意識**: リスキリングしたい社会人は、
**どのスキルが自分の職業に関係あるのか、矛盾する情報に圧倒されている**。
企業も政府も同じ問題を抱えている。

**手法**: **Singapore SkillsFuture Skills Framework** を土台に、
専門家の知識と労働市場データから抽出した情報を統合し、
**時間とともに更新される（動的な）知識グラフ**を構築。

**社内異動への含意**: スキル体系は**作って終わりではなく、更新され続ける必要がある**。
職務内容は変わるのに、社内のスキル定義だけが数年前のまま、という状況はよくあります。

同じチームが2025年に「スキルとタスクの対応づけ」の論文も出しています。

---

### 職業名の多言語リンクのベンチマーク（21言語）

> **MELO: An Evaluation Benchmark for Multilingual Entity Linking of Occupations**
> Federico Retyk, Luis Gascó, Casimiro Pio Carrino, Daniel Deniz, Rabih Zbib
> （**Avature Machine Learning**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_2.pdf
> コード・データ: https://github.com/Avature/melo-benchmark

**21言語・48データセット**。職業名の言及を **ESCO Occupations** の多言語タクソノミに
リンクするタスクの評価基盤。既存の高品質な人手注釈から構築されています。

**注目点**: 論文は「この重要な領域に、**一貫して進捗を測るための高品質な
公開評価ベンチマークが驚くほど不足している**」と述べています。

**日本語は対象外**です（21言語に含まれるか未確認）。

---

### 職種名の多言語エンコーダ

> **Combined Unsupervised and Contrastive Learning for Multilingual Job Recommendation**
> Daniel Deniz 他（**Avature Machine Learning**）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_3.pdf

**11言語**で職種名の意味的類似度をモデル化。
スキルと職種の共起情報で教師なし事前学習 → ESCO ベースの類似・非類似ペアで
対照学習によるファインチューニング、という**2段階の学習**。

英語で **mAP +4.3%**（従来の単言語SOTA比）。
言語をまたいだランキングも可能。

---

### 大規模なスキルマッチング（Malt）

> **Skill matching at scale: freelancer-project alignment for efficient
> multilingual candidate retrieval**
> Warren Jouanneau, Marc Palyart, Emma Jouffroy（**Malt**、登録フリーランサー70万人超）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_8.pdf

多言語事前学習モデルを土台に、**プロフィールと案件の構造を保つ**独自の
Transformer アーキテクチャを設計。履歴データで対照学習。

**注目点**: 同チームが2025年に「LLM蒸留」の論文を出しており、
**2024年は履歴データで学習 → 2025年はLLMを教師に**、と方針が変わっています。
理由は**履歴データの偏り**でした（2025年版サーベイ参照）。

**1年で方針を変えた事例**として、履歴データ依存のリスクを示しています。

---

### 計算資源が限られた環境でのスキル抽出

> **Hardware-effective Approaches for Skill Extraction in Job Offers and Resumes**
> Laura Vásquez-Rodríguez 他（**Idiap Research Institute**、スイス 他）
> https://ceur-ws.org/Vol-3788/RecSysHR2024-paper_9.pdf

**注目点**: 既存研究は**求人票**のスキル抽出に集中しており、
**職務経歴書（resume）を扱っていない**という指摘。

社内異動では扱うのは求人票ではなく**社員のプロフィール・経歴**なので、
こちらの系統の方が近いといえます。

---

## この回から読み取れる傾向

### 1. 「測れているのか」への問いが中心

| 論文 | 何を疑ったか |
|---|---|
| paper 6 (Indeed) | オフライン指標がオンライン成果を予測していない |
| paper 10 (TechWolf) | ベンチマークの正解データ自体が歪んでいる |
| paper 7 (Maastricht) | 説明を出しても意思決定が改善しない |
| paper 5 (Indeed) | 点推定ではモデル更新時の不安定性が見えない |

**10本中4本が評価・測定の問題**を扱っています。
手法を良くする前に、良くなったと言えるのかを問う年でした。

### 2. 産業界の参加が厚い

Indeed（2本）、Malt、Avature（2本）、TechWolf、Sony Network Communications、
GovTech Singapore、SkillsFuture Singapore。
**10本中8本に企業または政府機関が関与**しています。

### 3. 多言語対応が前提になっている

MELO（21言語）、職種エンコーダ（11言語）、Malt（多言語）。
ESCO を軸にした多言語対応が標準的な土台になりつつあります。
**ただし日本語は主要な対象になっていません。**

---

## 社内異動の観点で見たときの位置づけ

**社内異動を主題とした論文は無し**。ただし転用できる知見は多くあります。

| 論文 | 社内異動への転用 |
|---|---|
| paper 10（専門家発見） | **最も近い**。社内の人材発見と評価の落とし穴 |
| paper 6（評価段階） | どの段階を測っているのかを意識する |
| paper 5（安定性監視） | モデル更新時に推薦傾向が変わっていないか |
| paper 4（安定マッチング） | 一括異動調整の最適化 |
| paper 1（動的KG） | スキル体系は更新され続ける必要がある |
| paper 7（説明） | 根拠を出しても意思決定は改善しないかもしれない |

---

## 関連

- [RecSys in HR 2025 サーベイ](recsys-in-hr-2025.md)
- 全開催回: 2021 https://ceur-ws.org/Vol-2967/ ／ 2022 https://ceur-ws.org/Vol-3218/ ／
  2023 https://ceur-ws.org/Vol-3490/ ／ 2024 https://ceur-ws.org/Vol-3788/ ／
  2025 https://ceur-ws.org/Vol-4046/
