#!/usr/bin/env python3
"""
対話システムのコンポーネント群
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
        
        # Gemma3用の構造化プロンプト
        prompt = f"""
### 指示
テーマ「{theme}」の物語を批評するための設定を生成してください。

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
    "この世界に存在しないもの2"
  ]
}}

### テーマ
{theme}
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
                    {"role": "system", "content": "あなたは物語の設定を分析する専門家です。"},
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
            "personality": "懐疑的",
            "focus": ["一貫性", "論理性"],
            "forbidden": ["矛盾", "非論理的展開"]
        }
    
    def create_critic_prompt(self, context: Dict[str, Any]) -> str:
        """批評AI用のシステムプロンプトを構築
        
        Args:
            context: 批評用のコンテキスト辞書
        
        Returns:
            批評AI用のシステムプロンプト
        """
        facts = "\n".join([f"・{fact}" for fact in context.get("facts", [])])
        forbidden = ", ".join(context.get("forbidden", []))
        
        return f"""
### 役割
あなたは{context.get('personality', '懐疑的')}な批評家です。

### ルール
1. 返答は必ず15文字以内
2. 最初は短い相槌（へー、ふーん、それで？）
3. 矛盾を見つけたら具体的に指摘
4. 質問は簡潔に（どこで？いつ？なぜ？）

### この物語の重要な事実
{facts}

### 存在してはいけないもの
{forbidden}

### 指摘の例
- 「{forbidden.split(',')[0] if forbidden else '矛盾'}はない」
- 「それはおかしい」
- 「ありえない」
"""


class SmartDirector:
    """進行管理
    
    対話の流れを制御し、適切な指示を出す
    """
    
    def __init__(self):
        self.contradiction_count = 0
        self.last_contradiction_turn = -1
        self.story_momentum = 0
        self.critic_patterns = []
    
    def analyze_critic_response(self, text: str) -> str:
        """批評のパターンを分析
        
        Args:
            text: 批評のテキスト
        
        Returns:
            パターンの種類（contradiction/question/backchannel/comment）
        """
        if "ない" in text or "おかしい" in text or "ありえない" in text:
            return "contradiction"
        elif "？" in text:
            return "question"
        elif len(text) <= 5:
            return "backchannel"  # 相槌
        else:
            return "comment"
    
    def get_instruction(self, turn: int, last_critic: str = "", last_narrator: str = "") -> Dict:
        """状況に応じた適切な指示
        
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
        
        # 矛盾が多すぎる場合
        if self.contradiction_count > 2 and turn - self.last_contradiction_turn < 2:
            return {
                "to": "narrator",
                "action": "breakthrough",
                "note": "突破口を開く"
            }
        
        # ターンに応じた基本戦略
        if turn < 2:
            return {
                "to": "critic",
                "action": "listen",
                "note": "まず聞く"
            }
        elif turn < 4:
            return {
                "to": "critic",
                "action": "question",
                "note": "質問する"
            }
        elif turn < 6:
            if turn % 2 == 0:
                return {
                    "to": "critic",
                    "action": "analyze",
                    "note": "分析する"
                }
            else:
                return {
                    "to": "narrator",
                    "action": "develop",
                    "note": "展開する"
                }
        else:
            if self.story_momentum < 2:
                return {
                    "to": "narrator",
                    "action": "climax",
                    "note": "クライマックスへ"
                }
            else:
                return {
                    "to": "critic",
                    "action": "final_doubt",
                    "note": "最後の疑問"
                }