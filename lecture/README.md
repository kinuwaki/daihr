# 解説動画の生成パイプライン

このリポジトリの解説動画は、教科書HTMLから自動生成している。
`textbook/hr/ch01/index.html` を書き換えて再実行すれば、動画も作り直せる。

## 必要なもの

| | |
|---|---|
| VOICEVOX | 音声合成。起動しておく（`http://127.0.0.1:50021`） |
| ffmpeg | 動画結合 |
| Google Chrome | スライド描画（headless） |
| claude CLI | 台本生成。**従量課金** |

## 実行

```bash
cd lecture
python3 01_extract_outline.py --level hr --stats     # HTML → 構造JSON
python3 02b_build_lecture.py  --level hr --chapter 1 # 構造JSON → 台本
python3 03_review_script.py   --level hr             # 検証（必須）
python3 07_build_videos.py    --level hr --chapter 1 # スライド→音声→動画
python3 08_concat.py          --level hr --chapter 1 # 節ごとの動画を1本に結合
```

所要時間の実測（6節・25.7分の動画）: 台本生成 約3分 / 動画ビルド 11.4分。
音声合成が律速（VOICEVOXは1プロセスなので並列化しても速くならない）。

## 構成

```
01_extract_outline.py   教科書HTML → 構造JSON
02b_build_lecture.py    構造JSON → 台本（claude CLI）
03_review_script.py     記号の残存・読み辞書・尺・事実照合
04_render_slides.py     台本 → PNG 1920x1080
05_tts.py               台本 → 音声（VOICEVOX 春日部つむぎ speaker 8）
06_compose_video.py     PNG＋音声 → mp4 ＋ SRT
07_build_videos.py      04→05→06 をまとめて実行
08_concat.py            節ごとの mp4 と SRT を1本に結合（再エンコードなし）
templates/slide.css     スライドの見た目
dict/yomi.json          読み辞書
```

## 設計の核心

**スライドの文字と、しゃべる言葉は別物にする。**
教科書の文をそのまま画面に出して読み上げると「朗読」になり、プレゼンにならない。

| | 内容 |
|---|---|
| スライド | 要約。体言止めの短い要点 |
| 音声 | 話し言葉 |
| 字幕 | 音声と同じ（SRT自動生成） |

Mayer のマルチメディア学習理論の**冗長性の原理**——
ナレーション＋視覚は、ナレーション＋視覚＋全文テキストより学習効果が高い。

### 条文・表・事例はLLMに書かせない

素材のブロックに `[B0] [B1] …` と番号を振り、LLMには「このブロックを出す」と
番号で指定させる。スライドは教科書の実物から描く。LLMが書くのは speech だけ。
**これで表の数値が生成物で書き換わる余地が消える。**

### 対応づけは構造で保証する

「この文はこの要点の話」をLLMに申告させるとずれる。
生成の単位を「要点1つ＝しゃべり1本」にすれば、`focus` は要点の添字そのものなので
**光っている要点と声の内容は構造上ずれない**。

## 教科書HTMLの規約

パイプラインは意味づけされたHTMLに依存している。

```
section id="s1"   節（idが必須。無いと0節になる）
h2 / h3           見出し
p                 本文
law-box           制度・定義カード
pitfall-box       まちがえやすい点（term-x と対で使う）
case-box          事例
table.timeline    比較表
span.term         重要語 / span.term-x 誤り・否定
```

## 踏んだ落とし穴

- **section に id が要る** — `<section>` だけでは節として認識されず0節になる
- **LLMのJSONが末尾で壊れる** — バッチ分割と `repair_json()` で対処済み
- **尺は字数でなく個数で縛る** — 「合計○字」は守られない。「要点N個」なら安定する
- **記号は辞書では直らない** — `「」・%→` は前処理で潰す。`03` が残存を検査する
- **zoompan は使えない** — 静止画1枚13秒に実測217秒。クロスフェードのみにする
- **CSSは後勝ちに注意** — 追記後は必ず実物をレンダリングして見る
- **映像は音声より最大1フレーム短くなる** — `-r 25` だと映像長が 0.04 秒刻みに
  量子化されるため、音声長との差が最大 0.056 秒出る。字幕と音声は一致しているので
  実害は無い（最後のフレームが静止するだけ）。厳密に合わせたい場合は
  `-shortest` ではなく音声側に合わせて `-t` を明示する

## 音声の規約

VOICEVOX は商用可だが**キャラごとに個別規約**があり、クレジット表記が必須。
春日部つむぎ（speaker 8）は「VOICEVOX:春日部つむぎ」の表記のみで商用可。
クレジットは全スライドのフッタと最終スライドに入れてある。

## 出典

このパイプラインは別プロジェクト（検定教科書の講義動画化）で確立したものを移植した。
理論的な裏づけは以下。

- Mayer のマルチメディア学習理論（冗長性・シグナリング・時間的近接性）
- AutoLectures — https://arxiv.org/abs/2505.02966
- PPTAgent（slide-level functional types） — https://github.com/icip-cas/pptagent
