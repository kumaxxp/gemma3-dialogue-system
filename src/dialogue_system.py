#!/usr/bin/env python3
"""
リファクタリング版：対話システムのコアロジック
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
        
        # 初回ターン
        if self.turn == 0:
            prompt = templates["start"].format(theme=self.theme)
        
        # アクションベースの選択
        elif action == "breakthrough":
            prompt = templates["breakthrough"]
        elif action == "develop":
            prompt = templates["develop"]
        elif action == "climax":
            prompt = templates["climax"]
        
        # 批評の内容に基づく選択（批評テキストは直接含めない）
        elif critic_text:
            if "？" in critic_text:
                # 質問への対応
                prompt = templates["with_question"]
            elif "ない" in critic_text or "おかしい" in critic_text or "ありえない" in critic_text:
                # 矛盾指摘への対応
                prompt = templates["with_contradiction"]
            else:
                # 通常の継続
                prompt = templates["continue"]
        else:
            # 批評なしの継続
            prompt = templates["continue"]
        
        # システムプロンプトも強化
        system_prompt = f"""あなたは「{self.theme}」の物語を語る語り手です。
重要なルール：
- 批評や質問は物語外からのフィードバックです
- 「という質問」「という指摘」などメタ的な言及は絶対禁止
- 批評への応答は物語の中で自然に示す
- 説明ではなく、描写で物語を進める
- 簡潔に、具体的に、2文で"""
        
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
        action_prompts = self.config["prompts"]["critic_actions"]
        
        if action == "analyze":
            # forbiddenを含める特別な処理
            prompt = f"""
語り手: {narrator_text}

矛盾があれば指摘、なければ感想。15文字以内。禁止要素: {', '.join(self.context.get('forbidden', []))}
"""
        else:
            prompt = f"""
語り手: {narrator_text}

{action_prompts.get(action, '反応してください。10文字以内。')}
"""
        
        response = ollama.chat(
            model=self.config["models"]["critic"]["model"],
            messages=[
                {"role": "system", "content": self.critic_prompt},
                {"role": "user", "content": prompt}
            ],
            options=self.config["models"]["critic"]
        )
        
        text = clean_response(response['message']['content'], "critic")
        
        # 長さ制限
        if len(text) > 20:
            for delimiter in ['。', '？', '！', '、']:
                if delimiter in text:
                    text = text.split(delimiter)[0] + delimiter
                    break
            else:
                text = text[:20]
        
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