# 日本国内の人材マッチング技術 — サーベイ

日本国内の学会発表と企業技術ブログを対象にしたサーベイです。

**結論から言うと、国内アカデミアの層は薄く、知見は産業界の技術ブログに集中しています。**
特に**ビズリーチ（Visional）**は公開量・技術的深さともに突出しており、
学術論文より実務に近い知見が得られます。

主要なURLは実際に開いて内容を確認しています。
確認できなかったものは末尾に「未確認」として明記しています。

---

## 1. 最初に読むべき3本（すべて日本語・無料）

### 1-1. HR領域の検索は、ECの検索と根本的に違う

> **HR領域の検索が直面する課題 — 双方向マッチングの難しさと技術的挑戦**
> Visional Engineering Blog（2025年12月12日）
> https://engineering.visional.inc/blog/660/bizreach-search-core-group/

**何が違うか**: ECでは購入を決めるのは買い手だけ。
HR領域では**企業と求職者の双方が能動的に意思決定する**。

**片側最適化の罠（記事より）**:

| 何を最大化すると | 何が起きるか |
|---|---|
| 企業視点で「スカウト送信数」 | 求職者に興味のない求人が増える → **返信率が下がる** |
| 求職者視点で「応募数」 | 企業要件に合わない応募が増える → **書類通過率が下がる** |

マッチング成立には「企業がぜひ会いたい」と「求職者が進みたい」の
**両方が必要**なので、片側の指標だけを追うと全体が悪化します。

**技術的課題として挙げているもの**: Recall確保、双方向性を考慮したランキング、
カテゴリ値・テキスト・行動ログという性質の違うデータの統合、応答速度と精度の両立。

**取り組み**: ベクトルランキング、Interleaving、**SPLADE**
（転置インデックスによる高速検索と解釈性を両立する疎ベクトルモデル）。

**社内異動への含意**: 社内異動はさらに複雑で、**本人・受入部署・送出部署**の
三者が関与します。片側最適化の罠はそのまま当てはまります。

---

### 1-2. A/Bテストが機能しなかったので Interleaving にした

> **検索ランキングの比較のために Interleaving の導入と評価をした際の工夫**
> Visional Engineering Blog（2024年9月26日）
> https://engineering.visional.inc/blog/615/implement-interleaving-for-search-evaluation/

**出発点は失敗**（記事より）:
> **AAテストを実施したが、同じロジックを使った場合でも結果が大きく異なる問題が発生**

つまり**同じものを比較しているのに結果が違った**。A/Bテストが信用できない状態です。

**原因はHR領域固有の変動性**:

- 祝日の数、月初か月末か、期初か期末かで**採用にかける時間が変わる**
- 「エンジニアを2人採りたい」場合でも、**採用開始初期・選考中・1人決定後**で
  同じクエリへの行動がまったく変わる
- 「2週間や1ヶ月単位で比較する場合、ユーザーであるお客様の採用状況は全く異なる」

**なぜ Interleaving か**: 同じユーザーの同じクエリに対して2つのランキングを
交互に混ぜて提示するため、**ユーザー間のばらつきの影響を受けにくい**。

**手法の選択**: Balanced Interleaving。シンプルで実装・テストがしやすい。
ランダムクリックのバイアス懸念については、
**KPIがクリックより厳密な「メッセージ送信数」**なので影響は小さいと判断。

**実装上の工夫**: ページングが最大の課題。
1ページ目のみ Interleaving を実施し、結果を**1時間キャッシュ**して
2ページ目以降は除外して検索する。記事は「依然として複雑さが残っている」と認めています。

**社内異動への含意**: **年間数百件規模ではA/Bテストで有意差に到達できません。**
Interleaving はその状況で使える現実的な代替です。
社内異動には季節性（人事異動の時期）がさらに強く効くので、
この記事の問題意識はそのまま当てはまります。

---

### 1-3. MLシステムがブラックボックス化した話（失敗の記録）

> **ブラックボックス化したMLシステムの Vertex AI 移行**
> Visional Engineering Blog（2026年6月11日）
> https://engineering.visional.inc/blog/763/mlops_community_jp_202603/

転職意向予測モデルが**可観測性を失い、下流の利用先すら分からなくなった**という
率直な失敗記録です。

**社内異動への含意**: 人事システムは**作った人がいなくなった後も動き続けます**。
「なぜこの候補が出たか」を説明できないシステムは、
数年後に**誰も触れないブラックボックス**になります。

---

## 2. 学会発表

### 2-1. 学会誌『人工知能』特集「職場で働く AI」（2022）

国内で最もまとまった一次情報源です。
37巻2号、編集: 鹿内学・久米功一。ミイダス HRサイエンス研究所、Sansan、
リクルートワークス研究所が寄稿し、技術・法務・ガバナンスを横断しています。

目次: https://www.jstage.jst.go.jp/browse/jjsai/37/2/_contents/-char/ja

### 2-2. 人工知能学会全国大会（JSAI）

| 論文 | 発表 | URL |
|---|---|---|
| 強化学習によるマッチング数を最大化するジョブ推薦システム（脇聡志ほか、東大／エス・エム・エス）**既存手法比+131.2%以上** | JSAI2023 | [J-STAGE](https://www.jstage.jst.go.jp/article/pjsai/JSAI2023/0/JSAI2023_4Xin174/_article/-char/ja) |
| 人材領域における反実仮想機械学習を用いた相互推薦システム説明手法の提案（永安修也ほか） | JSAI2026 | [J-STAGE](https://www.jstage.jst.go.jp/article/pjsai/JSAI2026/0/JSAI2026_1I4GS4a04/_article/-char/ja) |
| 双方向推薦システムにおける長期的マッチング最大化（西村直樹ほか） | JSAI2026 | [J-STAGE](https://www.jstage.jst.go.jp/article/pjsai/JSAI2026/0/JSAI2026_5H2OS18a03/_article/-char/ja) |
| ジョブマッチングのための相互推薦手法の提案と評価（佐川靖宜・峯恒憲、九州大） | IEICE 2013 | [CiNii](https://cir.nii.ac.jp/crid/1520853835074766720) |

### 2-3. 言語処理学会（NLP年次大会）— 2024年以降に急増

**2019〜2026年の全プログラムを走査した結果、HR関連は2020〜2023年はゼロ、
2024年以降に急増**しています。**ビズリーチが3件を継続投稿**しており、
国内で最も体系的です。

| 論文 | 所属 | 年 | URL |
|---|---|---|---|
| 人材業界固有の表現を考慮した求人票のマルチラベル分類 | ビズリーチ | NLP2024 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2024/pdf_dir/P6-22.pdf) |
| Bi-encoder と kNN による職務記述書のスキルマッピング | 牧野拓哉（Megagon Labs／リクルート） | NLP2025 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2025/pdf_dir/P8-21.pdf) |
| 人材領域特化の LLM 教師付き長文BERT埋め込みモデルの構築 | ビズリーチ | NLP2026 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2026/pdf_dir/C7-6.pdf) |
| HRドメイン特化の疎ベクトル検索モデルの構築 | ビズリーチ | NLP2026 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2026/pdf_dir/Q9-10.pdf) |
| Japanese HR NIAH | SmartHR | NLP2026 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2026/pdf_dir/Q4-1.pdf) |
| **採用決定タスクを用いた LLM の年齢バイアス検出** | 一橋大・都立大 | NLP2026 | [PDF](https://www.anlp.jp/proceedings/annual_meeting/2026/pdf_dir/B2-4.pdf) |

**最後の1本は日本語での公平性研究として貴重**です。
海外の公平性研究は英語圏の属性（人種など）が中心で、
**日本の文脈（年齢）を扱った研究は稀**です。

### 2-4. 所見: 国内アカデミアには10年の空白がある

九州大・峯研究室（2012〜2013）以降、しばらく研究が途絶え、
**2023年以降に産業界主導で立ち上がっています**。

なお「人材マッチング」「タレントマネジメント」で CiNii を検索すると、
結果はほぼ金融機関・人事実務誌の記事で、**学術検索語としては機能しません**。

---

## 3. その他の企業技術ブログ

### ビズリーチ / Visional（最も情報量が多い）

| 記事 | 内容 |
|---|---|
| [HR特化SPLADEパイプライン](https://engineering.visional.inc/blog/728/hr-sparse-model-training-pipeline/) | 疎ベクトル検索の学習基盤 |
| [日本語SPLADE OSS公開](https://engineering.visional.inc/blog/721/bizreach-japanese-splade-oss/) | **OSS公開あり** |
| [DEIM2026レポート](https://engineering.visional.inc/blog/753/deim2026-report/) | 協調フィルタリング → BERT Two-Tower → Multi-Stage の変遷 |
| [研究総覧 NLP2024](https://engineering.visional.inc/blog/582/nlp2024/) | CB-Prior-CF ほか |

### レバレジーズ

> [「事業会社で研究はできない」は本当か？実データ×反実仮想でJSAI2026に挑んだ話](https://tech.leverages.jp/entry/2026/06/29/151710)

**「求職者は気に入っているが、企業側スコアが低いために推薦されない求人」**に対し、
**何が変わっていれば推薦されたか**を反実仮想で提示する手法。

社内異動でいえば「本人は行きたいが受入部署の評価が低くて候補に入らない」ケースに
相当します。**「なぜ推薦されなかったか」の説明**として直接参考になります。

### Wantedly

> [パーソナライズ推薦導入](https://www.wantedly.com/companies/wantedly/post_articles/1076653)

コールドスタート時にプロフィールの重みを動的に増やす。
**オフライン指標に頼れないため、社員による定性評価 → LLM仮想ペルソナ評価 →
A/Bテスト、という2段階を経て**判断している点が実務的です。

### SmartHR

> [HR領域のLLM評価方法論](https://tech.smarthr.jp/entry/2025/11/26/124958)

---

## 4. 海外企業（参考）

### Indeed

- [評価指標の選び方](https://engineering.indeedblog.com/blog/2025/11/normalized-entropy-or-apply-rate-evaluation-metrics-for-online-modeling-experiments/)
  — **プロダクト指標を主、モデル指標をガードレールに**
- [ユーザー埋め込み](https://engineering.indeedblog.com/blog/2026/06/distilling-long-tail-user-behavior-into-scalable-embeddings-for-job-search/)
  — メール推薦の応募率 +5.24% など具体的なA/B数値

### LinkedIn

- [Hiring Assistant のセマンティック検索](https://www.linkedin.com/blog/engineering/ai/semantic-search-for-ai-agents-at-scale-retrieval-and-ranking-for-linkedins-hiring-assistant)
  — 13億プロフィール、Two-tower + Matryoshka、高関連候補 +2.7%

**規模が3〜4桁違う**ため、手法をそのまま持ち込むことはできません。
考え方の参考として。

---

## 5. 日本語資源の空白

- **ESCO・TalentCLEF とも日本語は対象外**
- **HuggingFace の日本語データセット1,000件を全走査しても該当ゼロ**
  （調査時点。人材マッチング用の日本語公開データセットは見つからず）

現実的な経路は次の三段階になります。

1. TalentCLEF / SkillSpan（**CC BY 4.0**）など英語資源で手法を検証
2. 多言語モデル（multilingual-e5 など）を使う
3. 自社データで日本語に適応させる

**日本語の公開ベンチマークが無い**ことは、この分野で自社評価を
自前で設計しなければならない理由になります。

---

## 6. 未確認（正直な記録）

以下は**確認できませんでした**。存在しないという意味ではありません。

- **リクルート** — Recruit Data Blog に到達したが、求人推薦・マッチング・
  スキル抽出を主題とする記事は確認できず。「Two-Tower Model」タグの存在は
  見えたが記事本体に到達できず
- **LAPRAS / パーソルキャリア / エン・ジャパン / マイナビ** — 技術ブログのドメインが
  DNS解決失敗または接続拒否。**LAPRAS はスキル抽出・スコアリングで有力候補**のため
  再調査を推奨
- **DEIM**（データ工学と情報マネジメントに関するフォーラム）— 独自サイトで論文集を
  公開し CiNii/J-STAGE にほぼ未収録。**本サーベイでは1件も挙げていない**
- **JSAI ビジネス・インフォマティクス研究会（SIG-BI）** — シリーズの存在は確認したが、
  人材マッチング主題のセッション・論文は特定できず
- **日本版O-NET（job tag）の職業数・利用規約** — ボット対策により取得不可。
  **人手での確認を推奨**

---

## 関連

- [RecSys in HR 2025 サーベイ](recsys-in-hr-2025.md)
- [RecSys in HR 2024 サーベイ](recsys-in-hr-2024.md)
