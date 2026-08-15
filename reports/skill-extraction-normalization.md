# スキル定義化・スキル正規化 — 調査サーベイ

`design.md` では「スキル正規化（辞書 + LLM）」が1つの箱として書かれているだけだった。
その箱の中身について、**公開されている研究・資源で何が分かっているか**を調べた。

出典はすべて実際に開いて確認している。確認できなかったものは「未確認」と明記した。
本文書は調査結果の報告であり、採否の判断は含まない。

---

## 0. 要約

| 論点 | 調査で分かったこと |
|---|---|
| 用語 | 「スキル抽出」「識別」「標準化」「分類」は論文ごとに違う意味で使われている。統一定義が2024年のサーベイで初めて提案された |
| タスク構造 | 抽出（テキスト→スパン）と正規化（スパン→タクソノミID）は**別タスク**。後者が難しい |
| 性能の壁 | ESCO公式評価では、分類器の主な限界は**誤検出ではなく取りこぼし（false negative）** |
| 手法 | 同評価で**文字列マッチがLLMに対して競争力を持つ**と報告された |
| 日本語 | ESCO は28言語だが**日本語は非対応**。日本版O-NET（job tag）は数値情報中心で、スキルタクソノミとしての設計ではない |
| ベンチマーク | TalentCLEF が2025年に開始（76チーム）、2026年は113チームに拡大。**日本語は対象外** |

---

## 1. 用語が統一されていない、という前提

この分野を調べて最初に突き当たるのが、**同じ言葉が論文ごとに違うタスクを指す**という問題である。

> Senger, Zhang, van der Goot, Plank (2024)
> *Deep Learning-based Computational Job Market Analysis: A Survey on Skill Extraction and Classification from Job Postings*
> NLP4HR 2024（EACL併設ワークショップ）, pp.1–15
> https://aclanthology.org/2024.nlp4hr-1.1/

2023年11月までの**ニューラル手法によるスキル抽出論文26本**を対象としたサーベイ。
著者自身が「この分野にNLPの観点からの包括的レビューは存在しない」と述べている。

このサーベイの中心的な貢献が、**タスクの形式的な区別**である。
`skill extraction` / `identification` / `detection` / `standardization` / `classification`
が「異なる意味で、時に互換的に使われ、同じタスクも違うタスクも指す」現状に対し、
以下の定義を与えている（JP = 求人票、S = スキル集合、L = 細粒度ラベル）:

| 記号 | タスク | 定義 |
|---|---|---|
| **E** | Skill Extraction | `JP → S`。スキル関連情報を取り出す親カテゴリ |
| **I** | Skill Identification / Detection | 事前定義ラベルなしの抽出。`Span → {0,1}` の分類としても定式化される |
| **E_C** | Extraction with Coarse Labels | `JP → {SC₁…SCₙ}`。粗いカテゴリ付きのスパン抽出 |
| **Std** | Skill Standardization | `S → S'`。**スキル表記の正規化そのもの** |
| **C_D** | Direct Skill Classification | `S → L`。抽出済みスキルをタクソノミの細粒度ラベルへ写像 |
| **C_E** | Classification with Extraction | `JP → L`。求人票から直接ラベルへ（抽出を明示的に経ない） |

**この区別が実務上重要な理由**は、粒度（granularity）が手法によって違うためである。
同サーベイは抽出の単位を、求人票全体（E_JP）／文（E_sentence）／n-gram（E_n-gram）／
連続スパン（E_span）に分けている。「スキル抽出をやりました」という記述だけでは、
何を入力に何を出力したのか特定できない。

また **skill base（スキルベース）** の用語も整理されている。
階層構造を持つものが taxonomy、概念間の関係で構造を与えるものが ontology、
「skill dictionary」は多くの場合**非構造なスキルのリスト**を指して使われている。

### 定義：ハードスキルとソフトスキル

同サーベイは複数の定義を突き合わせた上で、以下に収束させている。

- **ハードスキル** — 測定可能な技術的スキルから、知識を学習・適用する一般的能力までを含む
  幅広い専門的能力。定量化でき、教育可能。ESCO の「知識（Knowledge）」カテゴリと
  O*NET の知識カテゴリを、ハードスキルの構成要素として統合できるとしている
- **ソフトスキル** — 個人的・社会的・知的コンピテンシー。
  ESCO では *transversal skills*（分野横断スキル）、
  O*NET では *Cross-Functional Skills* として位置づけられている

**注意点として同サーベイが指摘しているのは、ESCO のバージョン差**である。
Zhang ら (2022a,b) は ESCO v1.0 を使っているが、そのソフトスキルのカテゴリ定義は
現行版と異なる。Colombo ら (2019) は同じ ESCO 版を使いながらソフトスキルを
ハードスキルと分離して扱っている。
サーベイは「**スキルベースのどのバージョンの、どの部分集合を使ったかを明示すべき**」と
再現性の観点から勧告している。

---

## 2. 公開データセット（同サーベイ Table 1 より）

| データセット | 作成方法 | 粒度 | スキル種別 | タスク | 規模 |
|---|---|---|---|---|---|
| Sayfullina et al. 2018 | クラウドソーシング | span | soft | I | 7,411 spans |
| Green et al. 2022 | クラウドソーシング | span | hard+soft | E_C | 10,606 spans |
| Beauchemin et al. 2022 (FIJO) | 専門家 | span | soft | E_C | 47 JP / 932 spans |
| Zhang et al. 2022a (**SKILLSPAN**) | 専門家 | span | hard+soft | E_C | 265 JP / 9,633 spans |
| Zhang et al. 2022b (**KOMPETENCER**) | 専門家 | span | hard+soft | E_C + C_D | 60 JP / 920 spans |
| Decorte et al. 2022 (**DECORTE**) | 手作業 | span | hard+soft | I + C_D | 1,618 spans |
| Gnehm et al. 2022b (GNEHM-ICT) | 専門家 | span | hard+soft | E_C + C_D | 10,995 spans |
| Bhola et al. 2020 (BHOLA) | Skill Inventory | document | 不明 | C_E | 20,298 JP |

言語は英語・デンマーク語・フランス語・独語（スイス）など。
**規模はいずれも小さい**（最大でもスパン1万件台）ことが、この分野の制約として読み取れる。

主要なものの内容:

- **SKILLSPAN** (Zhang et al. 2022a) — スキルと知識のスパン注釈。
  HOUSE（2012–2020の社内求人）と TECH（StackOverflow求人、2020/6–2021/9）から成る。
  注釈ガイドラインは3名のドメイン専門家による反復的な改訂を経て公開されている
- **KOMPETENCER** (Zhang et al. 2022b) — デンマーク語。SKILLSPAN と同じ定義・ガイドライン。
  細粒度注釈は **ESCO API に問い合わせ、レーベンシュタイン距離で関連度を判定**する
  distant supervision で付与（＝人手の金標準ではない）
- **DECORTE** (Decorte et al. 2022) — SKILLSPAN の変種で ESCO ラベルを付与。
  KOMPETENCER と違い、**手作業で ESCO ラベルを突き合わせて金標準を作成**している
- **FIJO** — カナダの保険会社と共同。フランス語。ソフトスキルを
  「Thoughts / Results / Relational / Personal」の4クラスに分類

**注釈者が誰かによって「スキルとは何か」が変わる**点も明示されている。
ドメイン専門家、クラウドワーカー、求人を出した企業自身（Bhola et al. 2020 は
企業が付けたラベルを正解として使用）と様々で、サーベイは
自動ツール（AutoPhrase、Azure NER 等）で注釈した場合は
**自動化バイアスを避けるため人手検証を入れることを推奨**している。

---

## 3. 手法の系譜

### 3.1 抽出（Extraction）

サーベイは抽出を3系統に整理している。

1. **スパンラベリング** — 2018年 LSTM に始まり、2019年の BERT 以降は BERT 系が中心。
   Zhang et al. (2023) は **ESCO タクソノミを多言語 XLM-R の
   ドメイン適応事前学習に組み込み**、全スキル識別ベンチマークで当時のSOTAを更新。
   「ESCOのスキル名が短いため、短いスキルで特に性能が上がる」と報告
2. **二値分類** — 「この文/語はスキルを含むか」を判定
3. **粗ラベル付き抽出** — Gnehm et al. (2022a) の独語 jobBERT-de、
   Fang et al. (2023) の RecruitPro など、ドメイン適応の重要性が強調される系統

### 3.2 正規化・分類（Classification / Standardization）

**ここが「スキル正規化」の本体**にあたる。サーベイは2系統に分けている。

**(a) 類似度ベース**

埋め込み表現でスキル表記とタクソノミ項目を突き合わせる。
word2vec (2017) → FastText (2020、部分語情報でOOV対応) → sent2vec / SBERT (2021) と
テキスト埋め込みの進歩をそのまま反映している。

Zhang et al. (2022c) は RoBERTa / JobBERT で求人票のn-gramを ESCO と突き合わせ、
**文脈考慮型・頻度考慮型の埋め込み**も検証。
Gnehm et al. (2022a) は **オントロジーの階層構造を使って
ラベルマッチング用の正例ペアを作成**し、Siamese BERT を学習させている。

**(b) Extreme Multi-label Classification (XMLC)**

スキルベース全体（ESCO なら約13,000ラベル）を巨大なラベル集合とみなす定式化。
Bhola et al. (2020) が最初にこの形式化を行った（BHOLA データセットの約2,500ラベル）。

- Zhang et al. (2022b) — ESCO API による distant supervision、
  ゼロショット言語間転移でデンマーク語求人に適用
- Decorte et al. (2022) — 文レベルの XMLC。
  **負例サンプリング戦略**（ESCO階層上の兄弟ノード、レーベンシュタイン距離、
  RoBERTa埋め込みのコサイン類似度）を工夫
- Goyal et al. (2023) **JobXMLC** — 職種-スキルのグラフを構築し、
  GNN でマルチホップ埋め込みを取る

### 3.3 LLM の位置づけ

> Clavié & Soulié (2023)
> *Large Language Models as Batteries-Included Zero-Shot ESCO Skills Matchers*
> https://arxiv.org/abs/2307.03539

**ESCO 全13,000超スキルを対象に合成訓練データを生成**し、
類似度リトリーバで候補を出して**second LLM で再ランキング**する構成。
プロンプト時に**タスクを疑似プログラミングとして提示する**と性能が上がると報告。

報告値:
- 合成データにより RP@10 が distant supervision 比で **約10ポイント改善**
- GPT-4 再ランキングを加えると **22ポイント超の改善**
- 弱いモデルほど疑似プログラミング形式の恩恵が大きい

一方で、LLM が万能ではないことを示す結果もある。

> Nguyen et al. (2024) *Rethinking Skill Extraction in the Job Market Domain using LLMs*
> NLP4HR 2024 / https://arxiv.org/abs/2402.03832

in-context learning によるスキル抽出を6データセットで評価し、
**「教師あり手法には性能で及ばないが、構文的に複雑なスキル表現の扱いは優れる」**
というトレードオフを報告している。

---

## 4. ESCO 公式による分類器評価（2025）

この分野で最も直接的に「実際どれくらい効くのか」を測った文献。

> Marconi, Baer, Da Silveira, Gallais, Pruski (2025)
> *Evaluating ESCO skill classifiers*
> *Statistical Journal of the IAOS* / DOI: 10.1177/18747655251395229
> ESCO公式サイト掲載: https://esco.ec.europa.eu/en/about-esco/publications/publication/evaluating-esco-skill-classifiers

**背景**: ESCO のスキル分類器は広く使われているのに、
**数千規模のスキル集合に対する体系的評価は本研究以前に存在しなかった**。
理由は、①約14,000スキルという規模、②深刻なクラス不均衡。

**方法**: スキル×求人広告ペアの**層化・クラスタサンプリング**、専門家による注釈、
ブートストラップによる標準誤差推定で分類器を比較。

**結果として報告されていること**:

1. **主な限界は false negative（取りこぼし）であって false positive ではない**
   — 文字列マッチでもLLMベースでも、「求人票に含まれる関連スキルを
   すべて拾いきること」が課題であり、誤ったスキルを予測することではない
2. **分類器ごとに検出するスキルの集合が部分的にしか重ならない**
3. **文字列マッチ手法はLLMに対しても競争力のある性能を示す**

`design.md` の構成（辞書 + LLM）に関連する論点として、
公式評価が「辞書的手法はLLM比で競争力がある」「弱点は再現率側」と報告している点は
記録しておく価値がある。

---

## 5. ベンチマーク：TalentCLEF

この分野で唯一の公開共有タスク。

> Overview of the TalentCLEF 2025: Skill and Job Title Intelligence for Human Capital Management
> https://arxiv.org/abs/2507.13275

**2025年（第1回）**

| 項目 | 内容 |
|---|---|
| Task A | 多言語 職種名マッチング（英・西・独・中）。単言語＋言語横断 |
| Task B | 職種名からのスキル予測（英語） |
| データ | **実際の求人応募データ**を匿名化し人手注釈。言語的多様性と性別標識表現を反映 |
| 参加 | **76チーム登録・280超の投稿** |
| 手法傾向 | 多言語エンコーダ + **対照学習**によるIR的手法が主流。LLMはデータ拡張・再ランキングに使用 |
| 特記 | **ジェンダーバイアス評価**を評価設計に含む |

報告された知見として、**「モデルサイズ単体よりも学習戦略の影響が大きい」**。

**2026年（第2回）** — https://arxiv.org/pdf/2606.31692

- Task A: 文脈を考慮した求人-人材マッチング（英・西）
- Task B: 職種-スキルマッチング＋**スキル種別分類**（英語）。
  **core skill と contextual skill を区別**する設計に発展
- **113チーム登録・400超の投稿**へ拡大

いずれも**日本語は対象言語に含まれていない**。

関連ベンチマークとして **MELO**（Multilingual Entity Linking of Occupations、
https://arxiv.org/pdf/2410.08319）がある。
**21言語・48データセット**で、職業名の言及を ESCO Occupations へリンクする評価用。
（`recsys-in-hr-2024.md` に既出）

---

## 6. タクソノミ資源の実態

### ESCO

| 項目 | 値 |
|---|---|
| 職業数 | **3,039** |
| スキル・コンピテンス数 | **13,939** |
| 言語 | **28言語**（EU公用語 + アイスランド語・ノルウェー語・ウクライナ語・アラビア語） |
| スキル柱の構造 | 4分類 — Knowledge / Skills / Transversal skills / Language skills and knowledge |
| 入手 | ポータルのDownloadセクションおよびAPI。無償で参照可能 |

出典: https://esco.ec.europa.eu/en/classification/skill_main 、
https://esco.ec.europa.eu/en/about-esco/what-esco

**日本語は含まれない**（v1.2 の28言語に日本語なし)。
なお ESCO のスキル階層は「継続的な改善の過程にある」と公式に記載されており、
固定的な構造ではない。

### Lightcast Open Skills

| 項目 | 値 |
|---|---|
| スキル数 | **34,000以上** |
| 由来 | 数億件の求人票・プロフィール・履歴書から収集 |
| 更新 | **2週間ごと** |
| 提供条件 | **個人および非営利利用は無償**。Lightcast Open Skills Terms of Use に従う |

出典: https://lightcast.io/open-skills 、https://lightcast.io/open-skills/faqs

**注意**: `design.md` の表では「オープン」と記載しているが、
確認した範囲では**MIT/Apache のような標準的オープンソースライセンスではなく、
独自の Terms of Use** である。営利利用の条件は別途確認が必要（本調査では未確認）。

### 日本版O-NET（job tag）

厚生労働省が2020年3月開設。JILPT が職業情報データを開発し job tag に搭載している。

| 項目 | 内容 |
|---|---|
| 収録職業数 | **500超**（2024年4月時点で**531職業**との記述あり） |
| 提供内容 | 仕事内容、**タスク**、必要な学歴・資格・実務経験、労働条件、就労状況、**しごと能力プロファイル**（スキル、知識、仕事に対する興味、仕事に対する価値観） |
| 数値情報 | **スキルレベルや知識の重要度等を職業間で比較できるようスコア化** |
| 入手 | job tag サイトの「職業情報データダウンロード」機能 |

出典: https://www.jil.go.jp/activity/project/o-net/index.html 、
支援者向け活用ガイド Ver 3.0（厚労省職業安定局）

JILPT の開発報告書:
- 資料シリーズ No.286 (2024) — 2023年度入力データ開発
- 資料シリーズ No.271 (2023) — 2022年度
- 資料シリーズ No.260 (2022) — 2021年度

No.286 の記載として確認できた範囲では、**440職業を15の職業大分類**に分類し、
企業・団体ヒアリングと **Webモニター調査（2023年11月〜12月、有効回答21,599件）**で
数値情報を作成している。知識領域（KN項目）や仕事の性質領域（WC項目）が
項目ごとに異なる指標で評価されており、**項目間の直接比較は不可**とされている。

**本調査で確認できなかった点（未確認）**:
- ダウンロード可能なファイルの正確な形式・項目定義・スキル項目の総数
- 利用規約および再配布・商用利用の可否

理由: `shigoto.mhlw.go.jp` は **Imperva/Incapsula のボット保護**下にあり、
`/User/download` を含む各ページはプログラムからの取得が拒否される
（HTTP 200 だが本文はブロックページ）。ブラウザでの手動確認が必要。

**性格の違いとして記録しておくべき点**: job tag の数値情報は
**「職業 × 能力項目のスコア」**という構造であり、
ESCO / Lightcast のような**スキル概念のタクソノミ（ID体系・階層・別名辞書）**とは
設計思想が異なる。前者は職業間比較のための尺度、後者は表記を概念IDへ写像するための辞書である。

---

## 7. 日本語環境について

`survey.md` の「日本語の公開資源は無い」という記述を、本調査でも追認する結果となった。

- **ESCO** — 28言語に日本語なし
- **TalentCLEF** — 2025（英・西・独・中）、2026（英・西）。日本語なし
- **MELO** — 21言語。日本語の収録は未確認
- 主要な公開注釈データセット（SKILLSPAN、KOMPETENCER、DECORTE、FIJO、GNEHM-ICT、
  BHOLA、Green、Sayfullina）は**すべて非日本語**
- 日本語での求人票スキル抽出・正規化を主題とする査読付き研究は、
  本調査の検索範囲では特定できなかった

関連する日本語資源として確認できたもの:
- CiNii に「高齢者の履歴書からの特徴語抽出によるスキルの発見とマッチング」
  https://cir.nii.ac.jp/crid/1520572357009245440 （内容未確認）
- 日本語の**語彙正規化**（表記ゆれ）研究自体は言語処理分野に蓄積がある。
  ただしスキル領域を対象としたものではない

なお、SKILLSPAN 系の研究群が示すように、この分野の英語圏の進展は
**注釈ガイドラインを公開した小規模データセット**（数百求人票規模）から始まっている。

---

## 8. サーベイが挙げる未解決問題

Senger et al. (2024) が「今後の方向」として挙げているもの:

1. **Emerging skills（新出スキル）** — スキルベースを新技術・頻出キーワードで
   更新する手法（Javed et al. 2017、Khaouja et al. 2021b）はあるが、
   **標準ベンチマークがないため評価が困難**
2. **Implicit skills（暗黙のスキル）** — 求人票に直接書かれていないスキルの抽出。
   LLM で暗黙スキル入りの訓練データを生成する手法などが試みられている
3. LLM の適用は増えているが**十分な評価がなされていない**

同サーベイ自身の限界として、**英語で書かれた論文のみを対象**にした点、
トピックモデリング系を除外した点を明記している。

---

## 9. 出典一覧

**サーベイ・基礎文献**
- Senger, Zhang, van der Goot, Plank (2024) *Deep Learning-based Computational Job Market Analysis: A Survey on Skill Extraction and Classification from Job Postings* — https://aclanthology.org/2024.nlp4hr-1.1/
- Nguyen et al. (2024) *Rethinking Skill Extraction in the Job Market Domain using LLMs* — https://arxiv.org/abs/2402.03832
- Khaouja, Kassou, Ghogho (2021) *A Survey on Skill Identification from Online Job Ads*, IEEE Access 9:118134–118153

**評価・ベンチマーク**
- Marconi et al. (2025) *Evaluating ESCO skill classifiers* — https://esco.ec.europa.eu/en/about-esco/publications/publication/evaluating-esco-skill-classifiers
- TalentCLEF 2025 Overview — https://arxiv.org/abs/2507.13275
- TalentCLEF 2026 Overview — https://arxiv.org/pdf/2606.31692
- MELO: Multilingual Entity Linking of Occupations — https://arxiv.org/pdf/2410.08319

**手法**
- Clavié & Soulié (2023) *LLMs as Batteries-Included Zero-Shot ESCO Skills Matchers* — https://arxiv.org/abs/2307.03539
- Zhang et al. (2022a) *SkillSpan* — NAACL 2022
- Zhang et al. (2022b) *Kompetencer* — LREC 2022
- Decorte et al. (2022) *Design of Negative Sampling Strategies for Distantly Supervised Skill Extraction* — RecSys in HR 2022
- Goyal et al. (2023) *JobXMLC* — EACL Findings 2023
- *Enhancing Job Matching: Occupation, Skill and Qualification Linking with the ESCO and EQF taxonomies* — https://arxiv.org/abs/2512.03195

**タクソノミ資源**
- ESCO Skills & competences — https://esco.ec.europa.eu/en/classification/skill_main
- Lightcast Open Skills — https://lightcast.io/open-skills
- job tag（職業情報提供サイト） — https://shigoto.mhlw.go.jp/User/
- JILPT job tag 関連調査研究成果 — https://www.jil.go.jp/activity/project/o-net/index.html
