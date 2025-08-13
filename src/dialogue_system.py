#!/usr/bin/env python3
"""
改良版：批評反映機能を持つ対話システム
"""

import json
import re
from typing import Dict, List, Optional, Any

import ollama
from rich.console import Console
from rich.panel import Panel
from colorama import Fore, Style

from components import PromptGenerator, SmartDirector
from utils import clean_response

console = Console()


class DialogueSystem:
    """統合された対話システム
    
    語り手と批評者の対話を管理し、実行する
    """
    
    def __init__(self, theme: str, config_path: str = "config.json"):
        """
        Args:
            theme: 対話のテーマ
            config_path: 設定ファイルのパス
        """
        # 設定読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.theme = theme
        self.dialogue = []
        self.turn = 0
        
        # コンポーネント初期化
        self.prompt_generator = PromptGenerator(self.config)
        self.director = SmartDirector()
        
        # 批評用プロンプト生成
        self.context = self.prompt_generator.get_context(theme)
        self.critic_prompt = self.prompt_generator.create_critic_prompt(self.context)
        
        # デバッグ表示
        self._show_context()
    
    def _show_context(self):
        """生成されたコンテキストを表示"""
        console.print("\n[bold cyan]📋 生成された批評設定[/bold cyan]")
        console.print(f"性格: {self.context.get('personality', '不明')}")
        console.print(f"重要事実: {len(self.context.get('facts', []))}個")
        console.print(f"禁止要素: {', '.join(self.context.get('forbidden', []))}")
        console.print()
    
    def run_dialogue(self, max_turns: int = 10) -> List[Dict]:
        """対話の実行
        
        Args:
            max_turns: 最大ターン数
        
        Returns:
            対話履歴のリスト
        """
        console.print(Panel(f"[bold cyan]🎬 {self.theme}[/bold cyan]", expand=False))
        
        narrator_text = ""
        critic_text = ""
        
        for turn in range(max_turns):
            self.turn = turn
            
            # 進行役の判断
            instruction = self.director.get_instruction(turn, critic_text, narrator_text)
            console.print(f"[dim]進行→{instruction['to']}: {instruction['note']}[/dim]")
            
            # 語り手のターン
            if turn == 0 or instruction["to"] == "narrator":
                narrator_text = self.get_narrator_response(
                    critic_text,
                    instruction.get("action", "continue")
                )
                print(f"{Fore.MAGENTA}語り:{Style.RESET_ALL} {narrator_text}")
                self.dialogue.append({
                    "role": "narrator",
                    "content": narrator_text,
                    "turn": turn
                })
                self.director.story_momentum += 1
            
            # 批評のターン
            if turn < max_turns - 1 and (turn == 0 or instruction["to"] == "critic"):
                critic_text = self.get_critic_response(
                    narrator_text,
                    instruction.get("action", "listen")
                )
                
                # パターン分析
                pattern = self.director.analyze_critic_response(critic_text)
                if pattern == "contradiction":
                    console.print(f"[yellow]⚠️ 矛盾指摘: {critic_text}[/yellow]")
                
                print(f"{Fore.CYAN}批評:{Style.RESET_ALL} {critic_text}")
                self.dialogue.append({
                    "role": "critic",
                    "content": critic_text,
                    "turn": turn,
                    "pattern": pattern
                })
                
                # 批評後の語り手継続
                if instruction["to"] == "critic" and turn < max_turns - 2:
                    narrator_text = self.get_narrator_response(critic_text)
                    print(f"{Fore.MAGENTA}語り:{Style.RESET_ALL} {narrator_text}")
                    self.dialogue.append({
                        "role": "narrator",
                        "content": narrator_text,
                        "turn": turn
                    })
                    self.director.story_momentum += 1
            
            print("-" * 40)
        
        return self.dialogue
    
    def get_narrator_response(self, critic_text: str = "", action: str = "continue") -> str:
        """語り手の応答を生成
        
        Args:
            critic_text: 直前の批評テキスト
            action: 実行するアクション
        
        Returns:
            語り手の応答テキスト
        """
        templates = self.config["prompts"]["narrator_templates"]
        
        # 対話履歴を構築（直近の数ターン）
        recent_history = ""
        for entry in self.dialogue[-6:]:  # 直近6エントリ（約3往復）
            if entry["role"] == "narrator":
                recent_history += f"語り手: {entry['content']}\n"
            elif entry["role"] == "critic":
                recent_history += f"批評: {entry['content']}\n"
        
        # 初回ターン
        if self.turn == 0:
            prompt = templates["start"].format(theme=self.theme)
        else:
            # アクションに応じた基本プロンプト選択
            if action == "breakthrough":
                base_prompt = templates["breakthrough"]
            elif action == "develop":
                base_prompt = templates["develop"]
            elif action == "climax":
                base_prompt = templates["climax"]
            elif critic_text and "？" in critic_text:
                base_prompt = templates["with_question"]
            elif critic_text and ("ない？" in critic_text or "じゃない？" in critic_text):
                base_prompt = templates["with_contradiction"]
            else:
                base_prompt = templates.get("continue", "物語を自然に続けてください。")
            
            # 批評の内容を物語への指示として含める
            if critic_text:
                prompt = f"""
### これまでの対話
{recent_history}

### 直前の批評
批評: {critic_text}

### 指示
{base_prompt}

批評の指摘や質問を物語の中で自然に解決してください。
批評に言及せず、物語の描写として答えを示してください。
2文で簡潔に。
"""
            else:
                prompt = base_prompt
        
        # システムプロンプト
        system_prompt = f"""あなたは「{self.theme}」の物語を語る語り手です。

### 重要なルール
1. 物語の描写のみを行う
2. 批評への言及は絶対禁止（「という質問」「という指摘」など）
3. 批評の内容は物語の展開で自然に解決する
4. 具体的で視覚的な描写を心がける
5. 2文以内で簡潔に表現する

### 物語の一貫性
- 設定した世界観を守る
- 前の描写と矛盾しない
- 批評で指摘された点は修正または説明する"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = ollama.chat(
            model=self.config["models"]["narrator"]["model"],
            messages=messages,
            options=self.config["models"]["narrator"]
        )
        
        text = clean_response(response['message']['content'], "narrator")
        
        # 2文制限
        sentences = re.split(r'[。！？]', text)
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) > 2:
            text = '。'.join(sentences[:2]) + '。'
        
        return text
    
    def get_critic_response(self, narrator_text: str, action: str = "listen") -> str:
        """批評の応答を生成
        
        Args:
            narrator_text: 直前の語りテキスト
            action: 実行するアクション
        
        Returns:
            批評の応答テキスト
        """
        # 批評用の改良されたプロンプト
        forbidden_items = self.context.get('forbidden', [])
        facts = self.context.get('facts', [])
        
        # アクションに応じたプロンプト
        if action == "listen":
            instruction = "相槌を打って。5文字以内。（例：へー、ふーん、それで？）"
        elif action == "question":
            instruction = "短い質問をして。10文字以内。（例：どこで？、なぜ？、いつ？）"
        elif action == "analyze":
            instruction = f"""
矛盾や疑問があれば具体的に指摘。なければ短い感想。20文字以内。

### 禁止要素（これらは存在しないはず）
{', '.join(forbidden_items)}

### 指摘の例
- 「{forbidden_items[0] if forbidden_items else '水'}ってありえなくない？」
- 「それって矛盾してない？」
- 「〜じゃないの？」
"""
        elif action == "change_pattern":
            instruction = "いつもと違う反応を。感嘆や驚き。15文字以内。"
        elif action == "final_doubt":
            instruction = "最後の疑問や感想。15文字以内。"
        else:
            instruction = "反応して。10文字以内。"
        
        # 対話履歴を含める
        recent_history = ""
        for entry in self.dialogue[-4:]:  # 直近4エントリ
            if entry["role"] == "narrator":
                recent_history += f"語り手: {entry['content']}\n"
        
        prompt = f"""
### これまでの物語
{recent_history}

### 最新の語り
{narrator_text}

### 指示
{instruction}
"""
        
        # 改良された批評システムプロンプト
        enhanced_critic_prompt = f"""あなたは{self.context.get('personality', '懐疑的')}な批評家です。

### 基本ルール
1. 必ず20文字以内で返答
2. 断定的な否定（「ありえない！」）は避ける
3. 疑問形で優しく指摘する（「〜じゃない？」「〜なの？」）
4. 具体的な要素を挙げて質問する

### この物語の重要な事実
{chr(10).join(['・' + fact for fact in facts[:3]])}

### 良い批評の例
- 「水があるってありえなくない？」
- 「それって前と違わない？」
- 「場所はどこなの？」
- 「おお、展開が面白い！」

### 悪い批評の例
- 「ありえない！」（断定的すぎる）
- 「矛盾している」（具体性がない）
- 「違う」（短すぎて不親切）"""
        
        response = ollama.chat(
            model=self.config["models"]["critic"]["model"],
            messages=[
                {"role": "system", "content": enhanced_critic_prompt},
                {"role": "user", "content": prompt}
            ],
            options=self.config["models"]["critic"]
        )
        
        text = clean_response(response['message']['content'], "critic")
        
        # 長さ制限（20文字）
        if len(text) > 20:
            # 疑問符で終わるように調整
            if "？" in text:
                text = text.split("？")[0] + "？"
            else:
                for delimiter in ['。', '！', '、']:
                    if delimiter in text:
                        text = text.split(delimiter)[0]
                        if not text.endswith("？"):
                            text += "？"
                        break
                else:
                    text = text[:18] + "？"
        
        return text
    
    def analyze_dialogue(self) -> Dict[str, Any]:
        """対話の分析
        
        Returns:
            分析結果の辞書
        """
        analysis = {
            "total_turns": len(self.dialogue),
            "contradiction_count": self.director.contradiction_count,
            "patterns": {},
            "avg_length": {
                "narrator": 0,
                "critic": 0
            }
        }
        
        # パターン集計
        for entry in self.dialogue:
            if entry["role"] == "critic" and "pattern" in entry:
                pattern = entry["pattern"]
                analysis["patterns"][pattern] = analysis["patterns"].get(pattern, 0) + 1
        
        # 平均文字数
        narrator_lengths = [len(e["content"]) for e in self.dialogue if e["role"] == "narrator"]
        critic_lengths = [len(e["content"]) for e in self.dialogue if e["role"] == "critic"]
        
        if narrator_lengths:
            analysis["avg_length"]["narrator"] = sum(narrator_lengths) / len(narrator_lengths)
        if critic_lengths:
            analysis["avg_length"]["critic"] = sum(critic_lengths) / len(critic_lengths)
        
        return analysis