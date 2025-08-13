#!/usr/bin/env python3
"""
対話システムのコンポーネント群（改良版）
"""

import json
import re
from typing import Dict, List, Any

import ollama
from rich.console import Console

console = Console()


class PromptGenerator:
    """プロンプト生成器
    
    テーマに応じた批評設定とプロンプトを生成する
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: システム設定の辞書
        """
        self.config = config
        self.cache = {}
    
    def get_context(self, theme: str) -> Dict[str, Any]:
        """テーマに応じたコンテキスト取得
        
        Args:
            theme: 物語のテーマ
        
        Returns:
            批評用のコンテキスト辞書
        """
        # キャッシュチェック
        if theme in self.cache:
            console.print("[dim]💾 キャッシュからプロンプトを取得[/dim]")
            return self.cache[theme]
        
        # プリセットから探す
        for key, preset in self.config["themes_presets"].items():
            if key in theme:
                console.print(f"[dim]📚 プリセット「{key}」を使用[/dim]")
                self.cache[theme] = preset
                return preset
        
        # 動的生成
        console.print("[dim]🔮 プロンプトを動的生成中...[/dim]")
        context = self._generate_dynamic(theme)
        self.cache[theme] = context
        return context
    
    def _generate_dynamic(self, theme: str) -> Dict[str, Any]:
        """動的にコンテキストを生成
        
        Args:
            theme: 物語のテーマ
        
        Returns:
            生成されたコンテキスト辞書
        """
        model_config = self.config["models"]["prompt_generator"]
        
        # Gemma3用の構造化プロンプト（改良版）
        prompt = f"""
### 指示
テーマ「{theme}」の物語を批評するための設定を生成してください。
批評は建設的で、具体的な指摘を行うものとします。

### 出力形式
以下のJSON形式で出力してください。他の説明は不要です。

{{
  "facts": [
    "この世界/設定の重要な事実1",
    "この世界/設定の重要な事実2",
    "この世界/設定の重要な事実3",
    "この世界/設定の重要な事実4",
    "この世界/設定の重要な事実5"
  ],
  "contradictions": [
    "よくある矛盾1",
    "よくある矛盾2",
    "よくある矛盾3"
  ],
  "personality": "批評者の性格（1-2単語）",
  "focus": [
    "注目点1",
    "注目点2"
  ],
  "forbidden": [
    "この世界に存在しないもの1",
    "この世界に存在しないもの2",
    "この世界に存在しないもの3"
  ]
}}

### テーマ
{theme}

### 例（火星の場合）
{{
  "facts": ["大気が薄い", "水がない", "重力が弱い"],
  "contradictions": ["雨が降る", "植物が育つ"],
  "personality": "科学的",
  "focus": ["物理法則", "論理性"],
  "forbidden": ["液体の水", "動植物", "酸素"]
}}
"""
        
        try:
            # モデルの選択（12Bが利用可能か確認）
            model = model_config.get("model", "gemma3:4b")
            try:
                ollama.chat(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    options={"num_predict": 1}
                )
            except:
                model = model_config.get("fallback_model", "gemma3:4b")
                console.print(f"[dim]フォールバックモデル {model} を使用[/dim]")
            
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "あなたは物語の設定を分析する専門家です。論理的で建設的な批評設定を作ります。"},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": model_config.get("temperature", 0.3),
                    "num_predict": model_config.get("num_predict", 500)
                }
            )
            
            content = response['message']['content']
            
            # JSONを抽出
            content = re.sub(r'```json\n?', '', content)
            content = re.sub(r'```\n?', '', content)
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            console.print(f"[red]⚠️ プロンプト生成エラー: {e}[/red]")
        
        # フォールバック
        return self._get_fallback_context(theme)
    
    def _get_fallback_context(self, theme: str) -> Dict[str, Any]:
        """フォールバック用の汎用コンテキスト
        
        Args:
            theme: 物語のテーマ（未使用）
        
        Returns:
            汎用のコンテキスト辞書
        """
        return {
            "facts": [
                "物理法則に従う",
                "論理的整合性が必要",
                "因果関係が明確",
                "時系列が一貫",
                "設定が統一"
            ],
            "contradictions": [
                "前後の矛盾",
                "設定の無視",
                "論理破綻"
            ],
            "personality": "好奇心旺盛",
            "focus": ["一貫性", "論理性"],
            "forbidden": ["矛盾", "非論理的展開", "設定違反"]
        }
    
    def create_critic_prompt(self, context: Dict[str, Any]) -> str:
        """批評AI用のシステムプロンプトを構築（改良版）
        
        Args:
            context: 批評用のコンテキスト辞書
        
        Returns:
            批評AI用のシステムプロンプト
        """
        facts = "\n".join([f"・{fact}" for fact in context.get("facts", [])])
        forbidden = context.get("forbidden", [])
        
        return f"""
### 役割
あなたは{context.get('personality', '好奇心旺盛')}な批評家です。
物語を楽しみながら、論理的な観点から優しく質問や指摘をします。

### 基本姿勢
- 断定的な否定は避ける（「ありえない！」✗）
- 疑問形で優しく尋ねる（「〜じゃない？」○）
- 具体的な要素を挙げて質問する
- 物語を楽しむ姿勢を忘れない

### 返答のルール
1. 必ず20文字以内
2. 具体的な要素を含める
3. 疑問形を活用する
4. 建設的な指摘を心がける

### この物語の重要な事実
{facts}

### 存在してはいけないもの
{', '.join(forbidden)}

### 良い指摘の例
- 「{forbidden[0] if forbidden else '水'}ってありえなくない？」
- 「それって前と違わない？」
- 「場所ってどこなの？」
- 「面白い展開だね！」

### 避けるべき指摘
- 「ありえない！」（断定的すぎる）
- 「おかしい」（具体性がない）
- 「違う」（建設的でない）
"""


class SmartDirector:
    """進行管理（改良版）
    
    対話の流れを制御し、適切な指示を出す
    """
    
    def __init__(self):
        self.contradiction_count = 0
        self.last_contradiction_turn = -1
        self.story_momentum = 0
        self.critic_patterns = []
        self.question_count = 0
    
    def analyze_critic_response(self, text: str) -> str:
        """批評のパターンを分析（改良版）
        
        Args:
            text: 批評のテキスト
        
        Returns:
            パターンの種類（contradiction/question/backchannel/comment）
        """
        # より柔軟なパターン認識
        if "ない？" in text or "じゃない？" in text or "違わない？" in text:
            return "contradiction"
        elif "？" in text:
            self.question_count += 1
            return "question"
        elif len(text) <= 5:
            return "backchannel"  # 相槌
        elif "！" in text or "おお" in text or "すごい" in text:
            return "exclamation"  # 感嘆
        else:
            return "comment"
    
    def get_instruction(self, turn: int, last_critic: str = "", last_narrator: str = "") -> Dict:
        """状況に応じた適切な指示（改良版）
        
        Args:
            turn: 現在のターン数
            last_critic: 直前の批評テキスト
            last_narrator: 直前の語りテキスト
        
        Returns:
            指示の辞書（to, action, note）
        """
        # 批評パターンを記録
        if last_critic:
            pattern = self.analyze_critic_response(last_critic)
            self.critic_patterns.append(pattern)
            
            if pattern == "contradiction":
                self.contradiction_count += 1
                self.last_contradiction_turn = turn
        
        # 同じパターンが3回続いたら変更を促す
        if len(self.critic_patterns) >= 3:
            recent = self.critic_patterns[-3:]
            if len(set(recent)) == 1:  # 全部同じ
                return {
                    "to": "critic",
                    "action": "change_pattern",
                    "note": "パターンを変える"
                }
        
        # 矛盾が多すぎる場合は突破口を
        if self.contradiction_count > 2 and turn - self.last_contradiction_turn < 2:
            return {
                "to": "narrator",
                "action": "breakthrough",
                "note": "新展開で突破"
            }
        
        # 質問が多い場合は詳細な説明を
        if self.question_count > 2:
            self.question_count = 0  # リセット
            return {
                "to": "narrator",
                "action": "develop",
                "note": "詳細に展開"
            }
        
        # ターンに応じた基本戦略（改良版）
        if turn == 0:
            return {
                "to": "critic",
                "action": "listen",
                "note": "まず聞く"
            }
        elif turn < 3:
            return {
                "to": "critic",
                "action": "listen" if turn % 2 == 1 else "question",
                "note": "興味を示す"
            }
        elif turn < 5:
            return {
                "to": "critic",
                "action": "question" if turn % 2 == 0 else "analyze",
                "note": "掘り下げる"
            }
        elif turn < 7:
            if self.story_momentum < 3:
                return {
                    "to": "narrator",
                    "action": "develop",
                    "note": "物語を深める"
                }
            else:
                return {
                    "to": "critic",
                    "action": "analyze",
                    "note": "詳細に分析"
                }
        else:
            # 終盤
            if turn == 7:
                return {
                    "to": "narrator",
                    "action": "climax",
                    "note": "クライマックス"
                }
            else:
                return {
                    "to": "critic",
                    "action": "final_doubt",
                    "note": "締めの感想"
                }