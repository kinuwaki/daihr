# 社内異動支援AI — 手法カタログ

この文書は**判断材料**です。「こうすべき」ではなく「こういう選択肢があり、
それぞれこういう性質を持つ」を並べています。採否は読み手が決めてください。

すべての項目に出典URLを付けています。**URLを実際に開いて内容を確認したものだけ**を
載せ、確認できなかったものは「未確認」と明記しています。

作成日: 2026年8月15日

---

## 0. 最初に知っておくとよい3つの事実

### この分野には専門のワークショップがある

**RecSys in HR**（Recommender Systems for Human Resources）が ACM RecSys に併設され、
2021年から毎年開催されています。**論文は CEUR-WS で全文無料公開**されています。

- 2024（第4回、バーリ）: https://ceur-ws.org/Vol-3788/
- 2025（第5回、プラハ）: https://ceur-ws.org/Vol-4046/
- 2026（第6回、ミネアポリス、9月28日予定）: https://recsyshr.aau.dk/

求人推薦だけでなく、定着・育成・キャリア管理・人材プール管理・報酬まで
HR全般を扱う場です。**この分野で何が問題になっているかを掴むには、
まずここの論文タイトルを眺めるのが早い**です。

### 社内異動を扱った研究はほとんど無い

2024年・2025年の全論文を確認しましたが、**社内異動・内部人材モビリティを
正面から扱った論文はありませんでした**。ほぼすべてが外部採用（求人推薦）です。

つまり、社内異動の推薦は**学術的に空白地帯**です。
先行研究に従えばよい領域ではないので、設計判断の根拠は自分で残す必要があります。

### 「説明を出せば納得される」は実験で支持されていない

これは自分の想定を覆された研究です。

> Schellingerhout, Barile, Tintarev (2024).
> "Creating Healthy Friction: Determining Stakeholder Requirements of
> Job Recommendation Explanations." RecSys in HR 2024.
> https://arxiv.org/abs/2409.15971

30人を対象にした課題ベースのユーザ実験で、**本物の説明とランダムな説明とで、
意思決定の速度・精度に有意差が出ませんでした**。
信頼・有用性・透明性では本物が上回る傾向はあったものの、有意ではありません。

論文の結論は、説明を「説得の道具」ではなく
**「健全な摩擦（healthy friction）を生む意思決定支援」**として位置づけるべき、というものです。

実務上の含意は明確です。**「根拠を表示したから使ってもらえる」とは限りません。**
説明の有無より、担当者が立ち止まって検討する仕掛けになっているかが問われます。

---

## 1. 主要な学会・情報源

| 場 | 内容 | URL |
|---|---|---|
| **RecSys in HR** | HR特化ワークショップ。**最優先で見るべき** | https://recsyshr.aau.dk/ |
| ACM RecSys | 推薦システムの主要国際会議 | https://recsys.acm.org/ |
| SIGIR / KDD / WWW / CIKM | 情報検索・データマイニングの主要会議 | — |

2026年の RecSys in HR では **shared challenge（RecSys in HR WorkRB Challenge）**が
初めて実施されます。共通データセットでの比較評価が可能になるため、
手法選定の材料が増える見込みです。

*（各回の論文一覧は §4 に記載）*

---

## 2. 手法のカタログ

*（調査結果を反映予定）*

---

## 3. スキル体系・オントロジー

*（調査結果を反映予定）*

---

## 4. RecSys in HR の論文一覧

### 第4回（2024、ACM RecSys 2024 併設、バーリ）
出典: https://ceur-ws.org/Vol-3788/

| # | タイトル | 著者 | 分類 |
|---|---|---|---|
| 1 | A Dynamic Jobs-Skills Knowledge Graph | Seif, Toh, Lee | スキル体系 |
| 2 | MELO: An Evaluation Benchmark for Multilingual Entity Linking of Occupations | Retyk 他 | ベンチマーク |
| 3 | Combined Unsupervised and Contrastive Learning for Multilingual Job Recommendation | Deniz 他 | 推薦手法 |
| 4 | Parallel and Mini-Batch Stable Matching for Large-Scale Reciprocal Recommender Systems | Nakada, Kawamura, Furukawa | 両側マッチング |
| 5 | Enhancing Reliability in Recommendation Systems | Chen 他 | 信頼性 |
| 6 | Pseudo-online Measurement of Retrieval Recall for Job Recommendations | Wu, Pang, Cai | **評価方法** |
| 7 | Creating Healthy Friction: Determining Stakeholder Requirements of Job Recommendation Explanations | Schellingerhout, Barile, Tintarev | **説明可能性** |
| 8 | Skill matching at scale | Jouanneau, Palyart, Jouffroy | スキルマッチング |
| 9 | Hardware-effective Approaches for Skill Extraction | Vásquez-Rodríguez 他 | スキル抽出 |
| 10 | On the Biased Assessment of Expert Finding Systems | Decorte 他 | **公平性・評価バイアス** |

**社内異動を扱った論文は無し。**

### 第5回（2025、ACM RecSys 2025 併設、プラハ）
出典: https://ceur-ws.org/Vol-4046/

| # | タイトル | 著者 | 分類 |
|---|---|---|---|
| 1 | An Efficient Long-Context Ranking Architecture With Calibrated LLM Distillation: Application to Person–Job Fit | Jouanneau, Jouffroy, Palyart | LLM・ランキング |
| 2 | Benchmarking Predictive and Recommendation Models for Knowledge Work Productivity on the RLKWiC Dataset | Tachioka | ベンチマーク |
| 3 | Explained, yet misunderstood: How AI Literacy shapes HR Managers' interpretation of User Interfaces in Recruiting Recommender Systems | Kalff, Simbeck | **説明可能性・人事担当者** |
| 4 | Evaluating LLM Behavior in Hiring: Implicit Weights, Fairness Across Groups, and Alignment with Human Preferences | Hoffmann 他 | **LLM・公平性** |
| 5 | From Retrieval to Ranking: A Two-Stage Neural Framework for Automated Skill Extraction | Bielinski, Brazier | スキル抽出 |
| 6 | JoLA: Job Landscape Aware Job Recommendation | Nathan 他 | 推薦手法 |
| 7 | Mind the Task Gap: Unsupervised Skill–Task Link Prediction for Workforce Upskilling | Tan 他 | **スキルギャップ・育成** |
| 8 | Towards Explainable Job Title Matching: Leveraging Semantic Textual Relatedness and Knowledge Graphs | Zadykian 他 | 説明可能性 |
| 9 | Understanding and Defending Against Resume-Based Prompt Injections in HR AI | Akdemir, Levy | **セキュリティ** |

**社内異動を扱った論文は無し。**

注目すべき2本:

- **#3「Explained, yet misunderstood」** — 人事管理職がAIのUIをどう解釈するかを扱う。
  AIリテラシーによって解釈が変わるという指摘。導入時の教育設計に直結する
- **#9「Resume-Based Prompt Injections」** — 履歴書に仕込まれたプロンプトインジェクション。
  **LLMを推薦に使うなら避けて通れない攻撃面**。日本ではまだ話題になっていない

---

## 5. 公平性・監査

*（調査結果を反映予定）*

---

## 6. 規制

### EU AI Act

雇用分野のAIは **Annex III の高リスク**に分類されます。

**適用期限は2027年12月2日に延期されました**（Regulation (EU) 2026/1744、2026年7月27日発効）。
当初は2026年8月2日でした。

ただし**延期は義務の緩和ではありません**。Annex III 4項(b)は
「労働関係の条件、**昇進**または労働契約関係の終了に影響する決定」を明示しており、
**社内異動・昇進の推薦は明確に対象**です。準備期間が延びただけと捉えるべきです。

### 日本

**AI推進法**（2025年成立）は罰則のないソフトローで、バイアス監査の義務規定はありません。
実効的な拘束は次の3つです。

1. 個人情報保護法（評価データの目的外利用）
2. 労働法（職業安定法など）
3. EU圏の従業員を扱う場合の AI Act / GDPR の域外適用

実務指針は経産省・総務省「AI事業者ガイドライン」。

---

## 7. 確認できなかったこと

- RecSys in HR 第1〜3回（2021〜2023）の論文一覧
- 2026年 shared challenge の詳細（データセット・タスク）
- 日本国内の学会での該当研究
- 「社内異動先に知人がいると定着しやすい」を直接検証した研究
