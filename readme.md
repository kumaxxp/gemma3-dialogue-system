conda activate gemma-director
を使って実行する

# 🎭 Gemma3 対話システム

LLMを使用した創造的な対話生成システム。語り手と批評者の対話を通じて、動的で面白い物語を生成します。

## 📋 概要

このシステムは、Gemma3モデルを使用して2つの異なる役割（語り手と批評者）が対話形式で物語を展開していく創造的なAIシステムです。批評者が物語の矛盾や疑問点を指摘し、語り手がそれに応答することで、より豊かで論理的な物語が生成されます。

## 🚀 特徴

- **動的プロンプト生成**: テーマに応じた批評設定を自動生成
- **スマート進行管理**: SmartDirectorによる対話フローの最適化
- **リアルタイム分析**: 対話パターンと矛盾の追跡
- **GPU最適化**: NVIDIA RTX A5000 (24GB) での高速推論
- **柔軟な設定**: JSON設定ファイルによるカスタマイズ

## 📁 ファイル構造

```
src/
├── config.json          # システム設定ファイル
├── main.py             # エントリーポイント・UI
├── dialogue_system.py  # 対話システムのコアロジック
├── components.py       # プロンプト生成器・進行管理
├── utils.py           # ユーティリティ関数
└── outputs/           # 生成された対話の保存先
```

### 各ファイルの役割

#### `config.json`
- モデル設定（temperature、num_predict等）
- テーマプリセット（火星、コンビニ等）
- プロンプトテンプレート
- テーマリスト

#### `main.py` (約150行)
- プログラムのエントリーポイント
- Ollamaとモデルの確認
- テーマ選択UI
- 実行結果の表示

#### `dialogue_system.py` (約220行)
- `DialogueSystem`クラス: 対話の実行と管理
- 語り手・批評者の応答生成
- 対話履歴の管理
- 分析機能

#### `components.py` (約250行)
- `PromptGenerator`クラス: プロンプトの動的生成
- `SmartDirector`クラス: 対話フローの制御
- コンテキスト管理

#### `utils.py` (約80行)
- `clean_response()`: テキストクリーニング
- `check_ollama()`: Ollama接続確認
- `save_dialogue()`: 対話結果の保存

## 🔧 インストール

### 必要要件

- Python 3.8+
- Ubuntu 24.04 (推奨)
- NVIDIA GPU (推奨: RTX A5000)
- Ollama

### 依存パッケージのインストール

```bash
pip install ollama rich colorama
```

### Ollamaのセットアップ

```bash
# Ollamaのインストール
curl -fsSL https://ollama.ai/install.sh | sh

# 必要なモデルのダウンロード
ollama pull gemma3:4b
ollama pull gemma3:12b  # オプション（プロンプト生成用）
```

## 💻 使用方法

### 基本的な実行

```bash
cd src
python main.py
```

### 実行の流れ

1. システムがOllamaとモデルの存在を確認
2. テーマ選択画面が表示
3. 対話が自動的に実行
4. 結果が`outputs/`に保存

### 出力例

```
🎭 Gemma3 対話システム（リファクタリング版）
A5000 + Ubuntu 24.04 最適化版

✅ Ollama接続OK
✅ Gemma3:4b 検出

テーマを選択してください:
  1. 火星コロニーで発見された謎の信号
  2. 深夜のコンビニに現れた透明人間
  3. AIロボットが見た初めての夢

選択 (1-7): 1

📋 生成された批評設定
性格: 科学的
重要事実: 5個
禁止要素: 液体の水, 生物, 酸素

語り: 火星の赤い大地に設置された観測装置が、規則的なパルス信号を検出した。
批評: へー
語り: 信号は地下深くから発せられ、周期は正確に12.4秒だった。
批評: どこから？
...
```

## ⚙️ カスタマイズ

### config.json の編集

#### モデルパラメータの調整
```json
"narrator": {
  "model": "gemma3:4b",
  "temperature": 0.7,  // 創造性（0.0-1.0）
  "num_predict": 100,   // 最大トークン数
  "top_p": 0.9,        // 多様性
  "repeat_penalty": 1.1 // 繰り返し抑制
}
```

#### 新しいテーマプリセットの追加
```json
"themes_presets": {
  "カスタムテーマ": {
    "facts": ["事実1", "事実2"],
    "contradictions": ["矛盾1"],
    "personality": "性格",
    "focus": ["注目点1"],
    "forbidden": ["禁止要素1"]
  }
}
```

## 🔍 トラブルシューティング

### Ollamaに接続できない場合

```bash
# Ollamaのステータス確認
sudo systemctl status ollama

# Ollamaの起動
sudo systemctl start ollama

# Ollamaの再起動
sudo systemctl restart ollama
```

### モデルが見つからない場合

```bash
# インストール済みモデルの確認
ollama list

# モデルの再ダウンロード
ollama pull gemma3:4b
```

### GPUが認識されない場合

```bash
# NVIDIAドライバーの確認
nvidia-smi

# CUDAの確認
nvcc --version
```

## 📊 パフォーマンス

### 推奨スペック
- GPU: NVIDIA RTX A5000 (24GB VRAM)
- RAM: 32GB以上
- CPU: 8コア以上

### 実行速度の目安
- 対話生成: 約30秒/8ターン
- プロンプト生成: 約5秒
- 全体処理: 約40秒

## 🎯 今後の改善予定

- [ ] 批評の指摘を語りに反映させる機能の強化
- [ ] 対話履歴を活用した文脈理解の改善
- [ ] マルチモーダル対応（画像生成連携）
- [ ] Web UIの実装
- [ ] より多様な批評パターンの追加

## 📝 ライセンス

MIT License

## 🤝 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📧 連絡先

質問や提案がある場合は、GitHubのissueを作成してください。