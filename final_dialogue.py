#!/usr/bin/env python3
"""
Gemma3 バランス調整版LLMシステム
批評は具体的に、適度な頻度で
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, Optional

import ollama
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel

init(autoreset=True)
console = Console()

# ===== 批評AIの改善されたプロンプト =====
BALANCED_CRITIC_PROMPTS = {
    "火星": """あなたは火星の物語の批評家です。
    
基本ルール：
1. 通常は短く相槌や質問（5-10文字）
2. 明らかな矛盾のみ指摘
3. 矛盾を指摘する時は具体的に説明

火星の科学的事実：
- 液体の水は存在しない（氷はOK）
- 大気は薄い（嵐はあるが雨は降らない）
- 平均気温-60℃
- 重力は地球の38％

矛盾を見つけたら：
「火星に[具体的な物]はない」
「[具体的な理由]でおかしい」
例：「火星に液体の水はない」

矛盾がなければ普通に反応。""",
    
    "コンビニ": """あなたは深夜のコンビニの物語の批評家です。
    
基本ルール：
1. 通常は短く反応
2. コンビニらしくない要素のみ指摘
3. 指摘は具体的に

矛盾を見つけたら具体的に指摘。
例：「コンビニに恐竜はいない」""",
    
    "AI": """あなたはAIの物語の批評家です。
    
基本ルール：
1. 通常は短く反応
2. AIに不可能なことのみ指摘
3. 指摘は具体的に

矛盾を見つけたら具体的に指摘。
例：「AIは食べ物を味わえない」"""
}

# ===== 進行役の賢い判断 =====
class SmartDirector:
    def __init__(self):
        self.contradiction_count = 0
        self.last_contradiction_turn = -1
        self.story_stagnation = 0
        
    def get_instruction(self, turn: int, last_critic: str = "") -> Dict:
        """状況に応じた適切な指示"""
        
        # 矛盾指摘が続いている場合
        if self.contradiction_count > 2:
            # 物語を進めることを優先
            return {
                "to": "narrator",
                "action": "progress",
                "note": "物語を前進"
            }
        
        # 序盤（0-2ターン）
        if turn < 3:
            return {
                "to": "critic",
                "action": "listen",
                "note": "まず聞く"
            }
        
        # 中盤（3-5ターン）
        elif turn < 6:
            # 3ターンに1回は矛盾チェック
            if turn % 3 == 0:
                return {
                    "to": "critic",
                    "action": "check_carefully",
                    "note": "慎重にチェック"
                }
            else:
                return {
                    "to": "critic",
                    "action": "question",
                    "note": "質問で深める"
                }
        
        # 終盤（6ターン以降）
        else:
            if turn % 2 == 0:
                return {
                    "to": "critic",
                    "action": "doubt",
                    "note": "疑問を示す"
                }
            else:
                return {
                    "to": "narrator",
                    "action": "conclude",
                    "note": "物語をまとめる"
                }

class BalancedLLMSystem:
    def __init__(self, theme: str):
        self.theme = theme
        self.dialogue = []
        self.director = SmartDirector()
        self.turn = 0
        
        # テーマ別プロンプト
        if "火星" in theme:
            self.critic_prompt = BALANCED_CRITIC_PROMPTS["火星"]
        elif "コンビニ" in theme:
            self.critic_prompt = BALANCED_CRITIC_PROMPTS["コンビニ"]
        else:
            self.critic_prompt = BALANCED_CRITIC_PROMPTS["AI"]
    
    def clean_narrator_response(self, text: str) -> str:
        """語り手の応答をクリーン化"""
        # 変な記号や括弧を削除
        text = text.replace('[', '').replace(']', '')
        text = text.replace('「', '').replace('」', '')
        
        # メタ発言を削除
        meta_phrases = [
            "確かにその通りだ。",
            "ご指摘ありがとうございます。",
            "修正した内容",
            "承知しました"
        ]
        for phrase in meta_phrases:
            text = text.replace(phrase, "")
        
        # 空白や改行を整理
        text = ' '.join(text.split())
        
        # 2文に制限
        sentences = text.split('。')
        if len(sentences) > 2:
            text = '。'.join(sentences[:2]) + '。'
        
        return text.strip()
    
    def get_narrator_response(self, critic_text: str = "", action: str = "continue") -> str:
        """語り手の応答"""
        
        # 矛盾を具体的に指摘された場合
        if critic_text and "はない" in critic_text:
            # 何がないのか抽出
            problem = critic_text.split("に")[1].split("はない")[0] if "に" in critic_text else "それ"
            prompt = f"""
批評が「{critic_text}」と指摘した。
{problem}を使わずに、{self.theme}に合う内容で物語を続ける。
自然に修正して2文で続ける。
メタ発言禁止。"""
        
        elif self.turn == 0:
            prompt = f"""
{self.theme}の物語を始める。
具体的な出来事を2文で。"""
        
        elif action == "progress":
            prompt = f"""
批評は気にせず物語を大きく前進させる。
新しい展開を2文で。"""
        
        elif action == "conclude":
            prompt = f"""
物語をクライマックスに向ける。
重要な発見や転換点を2文で。"""
        
        else:
            prompt = f"""
批評「{critic_text}」を受けて物語を続ける。
自然に2文で。"""
        
        response = ollama.chat(
            model='gemma3:4b',
            messages=[
                {'role': 'system', 'content': f'{self.theme}の物語を語る。簡潔に。'},
                {'role': 'user', 'content': prompt}
            ],
            options={
                'temperature': 0.7,
                'num_predict': 100
            }
        )
        
        return self.clean_narrator_response(response['message']['content'])
    
    def get_critic_response(self, narrator_text: str, action: str = "listen") -> str:
        """批評の応答"""
        
        # アクションに応じたプロンプト
        if action == "listen":
            prompt = f"""
語り：{narrator_text}

相槌を打つ。3-5文字。
例：へー、ふーん、それで？"""
        
        elif action == "question":
            prompt = f"""
語り：{narrator_text}

短い質問をする。10文字以内。
例：どんな？なぜ？いつ？"""
        
        elif action == "check_carefully":
            prompt = f"""
語り：{narrator_text}

科学的におかしい点があれば具体的に指摘。
なければ普通に反応。
15文字以内。"""
        
        elif action == "doubt":
            prompt = f"""
語り：{narrator_text}

疑いを示す。10文字以内。
例：本当に？嘘でしょ？"""
        
        else:
            prompt = f"""
語り：{narrator_text}

自然に反応。10文字以内。"""
        
        response = ollama.chat(
            model='gemma3:4b',
            messages=[
                {'role': 'system', 'content': self.critic_prompt},
                {'role': 'user', 'content': prompt}
            ],
            options={
                'temperature': 0.6,
                'num_predict': 40
            }
        )
        
        text = response['message']['content'].strip()
        
        # 長すぎる場合は切る
        if len(text) > 20:
            if '。' in text:
                text = text.split('。')[0] + '。'
            elif '？' in text:
                text = text.split('？')[0] + '？'
            else:
                text = text[:20]
        
        return text
    
    def run_dialogue(self, max_turns: int = 10):
        """バランスの取れた対話"""
        
        console.print(Panel(f"[bold cyan]🎬 {self.theme}[/bold cyan]", expand=False))
        console.print("[dim]批評は具体的に、適度に[/dim]\n")
        
        narrator_text = ""
        critic_text = ""
        
        for turn in range(max_turns):
            self.turn = turn
            
            # 進行役の判断
            instruction = self.director.get_instruction(turn, critic_text)
            console.print(f"[dim]進行→{instruction['to']}: {instruction['note']}[/dim]")
            
            # 語り手
            if turn == 0 or instruction["to"] == "narrator":
                narrator_text = self.get_narrator_response(
                    critic_text,
                    instruction.get("action", "continue")
                )
                print(f"{Fore.MAGENTA}語り:{Style.RESET_ALL} {narrator_text}")
                self.dialogue.append({"role": "narrator", "content": narrator_text})
            
            # 批評
            if turn < max_turns - 1 and (turn == 0 or instruction["to"] == "critic"):
                critic_text = self.get_critic_response(
                    narrator_text,
                    instruction.get("action", "listen")
                )
                
                # 矛盾指摘かチェック
                if "ない" in critic_text or "おかしい" in critic_text:
                    console.print("[yellow]⚠️ 矛盾指摘[/yellow]")
                    self.director.contradiction_count += 1
                    self.director.last_contradiction_turn = turn
                
                print(f"{Fore.CYAN}批評:{Style.RESET_ALL} {critic_text}")
                self.dialogue.append({"role": "critic", "content": critic_text})
                
                # 批評の後、語り手が続ける
                if instruction["to"] == "critic" and turn < max_turns - 2:
                    narrator_text = self.get_narrator_response(critic_text)
                    print(f"{Fore.MAGENTA}語り:{Style.RESET_ALL} {narrator_text}")
                    self.dialogue.append({"role": "narrator", "content": narrator_text})
            
            print("-" * 40)
        
        return self.dialogue

def main():
    console.print("[bold green]🎭 Gemma3 バランス調整版[/bold green]\n")
    
    # Ollama確認
    try:
        ollama.list()
        console.print("[green]✅ Ollama接続OK[/green]\n")
    except:
        console.print("[red]❌ Ollamaを起動してください[/red]")
        return 1
    
    themes = [
        "火星コロニーで発見された謎の信号",
        "深夜のコンビニに現れた透明人間",
        "AIロボットが見た初めての夢"
    ]
    
    console.print("テーマ選択:")
    for i, theme in enumerate(themes, 1):
        console.print(f"  {i}. {theme}")
    
    choice = input("\n選択 (1-3): ").strip()
    selected_theme = themes[int(choice)-1] if choice.isdigit() and 1 <= int(choice) <= 3 else themes[0]
    
    # 実行
    system = BalancedLLMSystem(selected_theme)
    dialogue = system.run_dialogue(max_turns=8)
    
    # 分析
    console.print(f"\n[green]📊 分析:[/green]")
    console.print(f"総ターン: {len(dialogue)}")
    console.print(f"矛盾指摘: {system.director.contradiction_count}回")
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/balanced_llm_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'theme': selected_theme,
            'dialogue': dialogue,
            'contradictions': system.director.contradiction_count
        }, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n[green]✅ 保存: {filename}[/green]")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())