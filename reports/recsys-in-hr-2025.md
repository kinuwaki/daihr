# RecSys in HR 2025 — 全論文サーベイ

**The 5th Workshop on Recommender Systems for Human Resources**
ACM RecSys 2025 併設 ／ 2025年9月22〜26日 ／ プラハ

論文集: https://ceur-ws.org/Vol-4046/ （**全文無料公開**）
ワークショップ: https://recsyshr.aau.dk/

全9本のPDFを取得し、本文を読んで要約しています。
記載した数値はすべて論文本文からの引用です。

---

## この回を一言でいうと

**「LLMを人事に使うと何が起きるか」の年**でした。9本中4本がLLM絡みで、
うち2本は**LLMの危険性**を扱っています。手法の性能競争より、
**運用したときに何が問題になるか**に関心が移っています。

社内異動・内部人材モビリティを正面から扱った論文は**ゼロ**でした。

---

## 実務者が最初に読むべき3本

### 1. 説明UIを足しても「理解」は向上しない — むしろ下がることがある

> **Explained, yet misunderstood: How AI Literacy shapes HR Managers'
> interpretation of User Interfaces in Recruiting Recommender Systems**
> Yannick Kalff, Katharina Simbeck（HTW Berlin）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_3.pdf

**何をしたか**: ドイツの人事管理職 **410名**を対象にしたオンライン実験。
通常のダッシュボードと、3種類の説明（重要な特徴量・反実仮想・モデル基準）を
加えたものを比較した。

**わかったこと**:

- **実務で使われているダッシュボードは、そもそもAIの結果を説明していない。**
  AI要素を不透明なままにしている
- 説明を足すと、AIリテラシーが中〜高の人では**主観的な有用性・信頼は向上する**
- しかし**客観的な理解は向上しない。複雑な説明ではむしろ低下する**
- 高リテラシー層でのみ、「重要な特徴量のオーバーレイ」が理解を助けた

**論文の結論（引用）**:
> XAI is not a universal remedy to make AI, its functions, and results
> accessible to non-technical professionals.

**実務への含意**: 「根拠を表示すれば納得して使ってもらえる」は成り立ちません。
説明の設計は**利用者のAIリテラシーに合わせる必要があり**、
AI導入への投資は**リテラシー教育とセットでなければ効果が出ない**。

これは同じワークショップの2024年版
（[Creating Healthy Friction](https://arxiv.org/abs/2409.15971)、n=30）とも整合します。
そちらでは本物の説明とランダムな説明で意思決定の速度・精度に有意差が出ていません。

**2年連続で、独立した2つの実験が「説明を出せば済む」を否定している**という点が重要です。

---

### 2. 履歴書にプロンプトインジェクションが仕込める

> **Understanding and Defending Against Resume-Based Prompt Injections in HR AI**
> Arda Akdemir, Joshua H. Levy（**Indeed.com**）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_9.pdf

**何をしたか**: 履歴書に細工をしてLLMベースの特徴抽出を欺き、
候補者の資格を過大評価させる攻撃を分析。複数モデル・プロンプト手法・
出力形式で脆弱性を比較した。**実際の攻撃事例も提示**している。

**わかったこと（本文の数値）**:

| | 攻撃成功率 |
|---|---|
| 脆弱なモデル（対策なし） | **52.1% / 48.7%** |
| 出力形式を変えた場合 | 54.0% |
| gpt-4.1（そのまま） | 0.0%（高い耐性） |
| gpt-4.1-nano | 20.0% |
| 対策を適用後 | 52.1% → **0.0%** |

**実務への含意**: 求職者・社員が自分で書ける欄（自己申告スキル、キャリア希望、
職務経歴）をLLMに読ませるなら、**これは想定すべき攻撃**です。
社内システムでも「昇進したい社員が自己申告欄に細工する」動機は存在します。

論文は**対策を適用すれば成功率を0%にできる**ことも示しています。
日本ではまだほとんど議論されていない論点です。

---

### 3. LLMは何を重視して人を選ぶのか、経済学の手法で測る

> **Evaluating LLM Behavior in Hiring: Implicit Weights, Fairness Across Groups,
> and Alignment with Human Preferences**
> Morgane Hoffmann, Emma Jouffroy, Warren Jouanneau, Marc Palyart,
> Charles Pebereau（**Malt**、欧州最大のフリーランスマーケットプレイス）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_4.pdf

**何をしたか**: 労働経済学で人間の採用行動を分析する**実験計画法（完全要因計画）**を
LLMに適用。実際のフリーランスのプロフィールと案件記述から合成データを作り、
属性（スキル・単価・勤務形態など）を独立に変化させて、
**LLMが各属性にどれだけの重みを置いているかを推定**した。

**わかったこと**:

- LLMの評価は**標準的な経済理論とおおむね整合**する。
  プロフィールと案件の一致、プラットフォーム上の実績、業界経験を評価する
- 最も強いペナルティは**経験不足**と**プラットフォーム上の活動歴なし**
- 社会人口学的属性（性別・民族・学歴）への重みは**平均的には小さい**
- **ただし交差的な効果を見ると、生産性シグナルの重みが属性グループ間で異なる**

**実務への含意**: 「LLMは属性を見ていないから公平」とは言えません。
平均では差が無くても、**属性グループごとに「何を評価するか」が変わる**。

この論文の価値は結論より**方法論**にあります。
完全要因計画で合成データを作り、LLMの暗黙の重みを推定する枠組みは、
**自社で導入するLLMの挙動を監査する手順としてそのまま使えます**。

---

## 手法系の論文

### スキル抽出を2段階（検索→ランキング）で行う

> **From Retrieval to Ranking: A Two-Stage Neural Framework for Automated Skill Extraction**
> Aleksander Bielinski, David Brazier（Edinburgh Napier University）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_5.pdf
> コード: https://github.com/AleksanderB-hub/Multi-Stage-Pipeline-Skill-Extraction

bi-encoder で候補スキルを高速に検索し、cross-encoder で精密に順位付けする。
**ESCO（約14,000スキル）**を使い、公開データセットで評価。

| | 改善幅 |
|---|---|
| bi-encoder（RP@5） | 既存ベースライン比 **+4.78ポイント** |
| cross-encoder（micro-F1） | **LLMベースのランキング比 +30.54ポイント** |

**注目点**: LLMにランキングさせるより、**専用モデルを訓練した方が大幅に良い**。
「とりあえずLLM」への反証になります。未知スキルへのゼロショット性能も良好。
コード公開あり。

---

### 長文の職務経歴を効率よくランキングする（LLM蒸留）

> **An Efficient Long-Context Ranking Architecture With Calibrated LLM Distillation:
> Application to Person–Job Fit**
> Warren Jouanneau, Emma Jouffroy, Marc Palyart（**Malt**、フリーランサー85万人超）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_1.pdf

**課題**: 職務経歴も案件記述も長く、構造化されていて、多言語。
リアルタイム推論が必要だが、Transformerは入力長に制限があり計算も重い。

**手法**: late cross-attention アーキテクチャで長文を分解して扱う。
**生成LLMを教師として使い、意味的に根拠のある教師信号を作って
軽量な生徒モデルに蒸留**する。

**なぜLLMを教師にするか（重要）**:
> 実際の推薦システムのログは疎で偏っている（選択バイアス・露出バイアス）。
> 履歴データから学習すると、その偏りを再生産する。

**実務への含意**: **過去の異動履歴を教師にすると過去の偏りを学習する**という問題への、
一つの回答です。履歴の代わりにLLMの判断を教師にする。
社内異動でも「過去の慣行を再現してしまう」問題は同じなので、参考になります。

---

### 職種名のマッチングを知識グラフで説明可能にする

> **Towards Explainable Job Title Matching: Leveraging Semantic Textual Relatedness
> and Knowledge Graphs**
> Vadim Zadykian, Bruno Andrade, Haithem Afli（ADAPT Centre, Munster Technological University）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_8.pdf

埋め込みだけでは「なぜ似ているか」を説明できない（ブラックボックス）ため、
**ドメイン固有の知識グラフを組み合わせる**。

**方法論として優れている点**: 全体の平均性能だけを見るのではなく、
**意味的関連度を「低・中・高」の帯に分けて評価**している。

> 高STR帯では、強いベースライン比で **RMSE が25%改善**

論文は「全体指標が隠してしまう強みと弱みが、帯別分析で見える」と述べています。
**評価の仕方として、そのまま真似する価値があります。**

---

### 人気求人への集中を避ける（orphan job 問題）

> **JoLA: Job Landscape Aware Job Recommendation**
> Solal Nathan 他（INRIA/CNRS、**France Travail**＝フランス公共職業安定所、CREST 他）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_6.pdf
> コード: https://codeberg.org/solal/jola

**問題意識**: 求人推薦は**混雑（congestion）**を生む。人気求人ばかり推薦すると
応募が集中し、一方で**応募がほとんど来ない「孤児求人（orphan job）」**が生まれる。
これは市場の不均衡を悪化させ、長期的には企業が求人を出さなくなる。

**手法**: 求人が獲得する市場シェアの微分可能な近似を使い、
混雑と孤児求人を防ぐ新しい損失関数を提案。

**社内異動への示唆**: 同じ構造が社内でも起きます。
**人気部署にばかり候補が集まり、地味な部署には誰も推薦されない。**
推薦の精度だけを最適化すると、この偏りは見えません。

公共職業安定所が著者に入っている点も注目に値します。

---

### スキルとタスクの関係を教師なしで推定する（政府事例）

> **Mind the Task Gap: Unsupervised Skill–Task Link Prediction for Workforce Upskilling**
> Yee Sen Tan 他（**SkillsFuture Singapore**、**シンガポール政府技術庁**）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_7.pdf

**何をしたか**: シンガポールの労働市場の知識グラフを構築。

| 対象 | 件数 |
|---|---|
| 職務ロール | 1,869 |
| タスク | 27,159 |
| スキル | 3,100 |
| 認定講座 | 28,313 |

**課題**: スキルとタスクを結ぶリンクが存在しない。これを教師なしの
グラフ補完問題として解いた。**GPT-4o による疑似ラベル5万件**を使い、
Variational Graph Autoencoder（GCNエンコーダ）で **macro-F1 0.6039** を達成。
意味的類似度のベースラインを大きく上回った。

**検証の誠実さ**: 疑似ラベルの妥当性を確認するため500ペアを無作為抽出し、
**90%以上が内部タクソノミーと整合**することを確認。
そのうえで「人手検証の代替にはならない」と明記している。

**実務への含意**: スキル体系を持っていても、**スキルと実際の業務タスクの
対応づけが欠けている**のはよくあります。それを埋める方法として参考になります。
政府機関が公開している点で、公共性のある取り組みの例としても使えます。

---

### 知識労働者の生産性ベンチマーク（日本からの発表）

> **Benchmarking Predictive and Recommendation Models for Knowledge Work
> Productivity on the RLKWiC Dataset**
> Yuuki Tachioka（**デンソーアイティーラボラトリ**、東京）
> https://ceur-ws.org/Vol-4046/RecSysHR2025-paper_2.pdf

RLKWiC データセット（実際のデジタル作業環境の行動ログ）に対して、
6つの実務的タスク（コンテキスト検出、活動分類、Webドメイン・イベント・
アプリの逐次予測）のベンチマークを定義し、コードを公開した。

論文は、これらが**職場分析・研修支援・ウェルビーイング監視**といった
HR応用の部品になると述べています。

**注意点**: 行動ログの活用は**従業員監視と受け取られるリスク**が大きい領域です。
日本企業からの発表という点で参考になりますが、導入判断は慎重に。

---

## この回から読み取れる傾向

### 1. 関心が「精度」から「運用したら何が壊れるか」へ移っている

9本中、純粋な精度改善は3本程度。残りは**説明の効果測定・攻撃耐性・
LLMの挙動監査・市場の混雑**といった、運用面の問題を扱っています。

### 2. 「とりあえずLLM」への反証が複数ある

- スキル抽出は**専用モデルがLLMランキングを30ポイント上回る**（paper 5）
- LLMベースの抽出は**プロンプトインジェクションで54%欺ける**（paper 9）
- LLMは属性グループごとに**評価基準が変わる**（paper 4）

LLMを使うなら、**教師として使って軽量モデルに蒸留する**（paper 1）方が
筋が良い、という方向が見えます。

### 3. 説明可能性は「出せばよい」段階を過ぎている

2024年（n=30）と2025年（n=410）の独立した2実験が、
**説明を出しても客観的な理解は向上しない**ことを示しています。
リテラシーに応じた設計と教育がセットで必要、というのが現時点の到達点です。

### 4. 公的機関の参加が目立つ

France Travail（フランス公共職業安定所）、SkillsFuture Singapore、
シンガポール政府技術庁。労働市場のインフラとして扱われ始めています。

---

## 社内異動を考えるときの位置づけ

**この分野の研究は、ほぼすべて外部採用（求人推薦）を前提としています。**
社内異動には次の違いがあり、そのまま適用できません。

| | 外部採用（研究の前提） | 社内異動 |
|---|---|---|
| データ量 | 数百万〜数億件の応募ログ | **年間数百件** |
| 候補者の情報 | 履歴書のみ（自己申告） | **評価・異動履歴・スキルが既にある** |
| 目的 | 応募率・採用成立 | 定着・育成・組織の充足 |
| 失敗のコスト | 応募が来ないだけ | **異動失敗＝退職** |
| 当事者 | 求職者・採用側 | 本人・受入部署・**送出部署** |

とはいえ、**問題の構造は共通するものが多い**です。

- 混雑と孤児求人（paper 6）→ 人気部署への集中と、誰も来ない部署
- 履歴データの偏り（paper 1）→ 過去の異動慣行の再生産
- 説明の限界（paper 3）→ 人事担当者が根拠を正しく解釈できるか
- プロンプトインジェクション（paper 9）→ 自己申告欄への細工

**「社内異動の研究が無い」ことは、参考にできないという意味ではありません。**
どの知見がどこまで転用できるかを、自分で判断する必要があるという意味です。

---

## 過去回で、社内異動に最も近い論文

2025年には無かったが、**過去回には社内異動を明示した論文がある**。

> **Career Path Prediction using Resume Representation Learning and Skill-based Matching**
> Jens-Joris Decorte 他（Ghent University – imec / **TechWolf**）
> RecSys in HR 2023
> https://ceur-ws.org/Vol-3490/RecSysHR2023-paper_1.pdf

アブストラクトに「応用先は **turnover prevention（離職防止）と internal job mobility
（社内異動）**」と明記されている。**本ワークショップ全5回で、社内異動を
正面から応用先に挙げた数少ない論文**（本文を取得して確認済み）。

- **2,164件**の匿名キャリア履歴に ESCO 職業ラベルを付与したデータセットを構築
- CareerBERT（職務経歴データ向けの表現学習）を提案

| 手法 | recall@10 |
|---|---|
| スキルベース | 35.24% |
| テキストベース | 39.61% |
| **ハイブリッド** | **43.01%** |

**注目点**: 既存手法は大量の非公開キャリア履歴データを必要とするが、
本手法は**職務経歴書の自由記述テキスト**を使う。
データが少ない環境で使える方向性として参考になる。

なお recall@10 が43%ということは、**10件出して正解が入るのが半分以下**。
この分野の難しさを示す数字でもある。

---

## 次に見るとよいもの

### RecSys in HR の全開催回（すべて全文無料）

| 回 | 年 | 開催地 | URL |
|---|---|---|---|
| 1st | 2021 | Amsterdam | https://ceur-ws.org/Vol-2967/ |
| 2nd | 2022 | Seattle | https://ceur-ws.org/Vol-3218/ |
| 3rd | 2023 | Singapore | https://ceur-ws.org/Vol-3490/ |
| 4th | 2024 | Bari | https://ceur-ws.org/Vol-3788/ |
| 5th | 2025 | Prague | https://ceur-ws.org/Vol-4046/ |
| 6th | 2026 | Minneapolis | https://recsyshr.aau.dk/ |

DBLP索引: https://dblp.org/db/conf/hr-recsys/index.html

### WorkRB — 共通ベンチマークが登場した

2026年から **shared challenge** が始まり、その基盤として
**WorkRB**（work領域AI向けのオープンソース・ベンチマーク）が公開された。

- **7タスク群13タスク**（職業↔スキル、候補推薦、スキル抽出・正規化など）
- 最大28言語、**Apache 2.0**
- `pip install workrb` で利用可
- https://workrb.techwolf.ai/ ／ 論文 https://arxiv.org/abs/2604.13055

**プロプライエタリなタスクを機密データを露出せずに統合できる**設計とされており、
自社データで評価に参加できる。手法選定の材料として今後の中心になる可能性がある。

*（未確認: WorkRB の詳細仕様は論文本文を確認していない）*
