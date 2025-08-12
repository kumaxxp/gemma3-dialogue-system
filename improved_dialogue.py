#!/usr/bin/env python3
"""
Gemma3 Three-Role Dialogue System - 改善版
より短く、より自然な会話を生成
"""

import os
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import ollama
from colorama import init, Fore, Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

init(autoreset=True)
console = Console()

# ===== 改善されたプロンプト =====
PROMPTS_V2 = {
    "narrator": """あなたは物語の語り手です。
重要なルール：
- 物語だけを語る（メタ的な説明は一切しない）
- 批判されたら感情的に反応する
- 1回の発言は2-3文程度に収める
- 進行指示が来たら、その感情と長さに従う""",
    
    "critic": """あなたは意地悪な批評家です。
重要なルール：
- 理由なく否定することが多い
- 「で？」「だから？」「つまらない」など短く切り捨てる
- たまに長く批判することもある
- 進行指示の感情に従う""",
    
    "director": """あなたは会話の演出家です。
次のJSON形式のみで応答：
{"to": "narrator|critic", "emotion": "angry|defensive|dismissive", "length": "short|long", "sample": "使うフレーズ例"}
内容には干渉せず、形式と感情のみ指示する。"""
}

# ===== 設定クラス =====
@dataclass
class SystemConfigV2:
    """改善版システム設定"""
    model_4b: str = "gemma3:4b"
    model_12b: str = "gemma3:12b"
    
    # パラメータ調整
    temperature_narrator: float = 0.8  # 創造性
    temperature_critic: float = 0.7    # やや抑えめ
    temperature_director: float = 0.3  # 一貫性重視
    
    max_tokens_narrator: int = 150
    max_tokens_critic: int = 100
    max_tokens_director: int = 50

# ===== 改善版対話システム =====
class ImprovedDialogueSystem:
    def __init__(self, config: SystemConfigV2):
        self.config = config
        self.conversation_history = []
        self.turn_count = 0
        
    def get_response(self, role: str, prompt: str, instruction: Dict = None):
        """役割に応じた応答を取得（パラメータ調整付き）"""
        
        # システムプロンプト構築
        system_prompt = PROMPTS_V2[role]
        
        # 進行指示がある場合は追加
        if instruction and role != 'director':
            if instruction.get('to') == role:
                system_prompt += f"\n\n【演出指示】\n"
                system_prompt += f"感情: {instruction.get('emotion', 'neutral')}\n"
                system_prompt += f"長さ: {instruction.get('length', 'medium')}\n"
                if instruction.get('sample'):
                    system_prompt += f"フレーズ例: {instruction['sample']}\n"
        
        # 温度設定
        temp_map = {
            'narrator': self.config.temperature_narrator,
            'critic': self.config.temperature_critic,
            'director': self.config.temperature_director
        }
        
        # トークン制限
        token_map = {
            'narrator': self.config.max_tokens_narrator,
            'critic': self.config.max_tokens_critic,
            'director': self.config.max_tokens_director
        }
        
        try:
            response = ollama.chat(
                model=self.config.model_4b,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': temp_map[role],
                    'num_predict': token_map[role],
                    'top_p': 0.9,
                    'top_k': 40
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            console.print(f"[red]エラー ({role}): {e}[/red]")
            return None
    
    def analyze_conversation_state(self):
        """会話の状態を分析（シンプル版）"""
        if len(self.conversation_history) < 2:
            return "start"
        
        # 最近の会話の長さをチェック
        recent = self.conversation_history[-2:]
        avg_length = sum(len(h['content']) for h in recent) / len(recent)
        
        if avg_length > 300:
            return "too_long"
        elif avg_length < 50:
            return "too_short"
        
        # 同じような応答が続いているか
        if self.turn_count > 3 and self.turn_count % 3 == 0:
            return "needs_variation"
        
        return "normal"
    
    def generate_director_instruction(self, state: str):
        """状態に応じた演出指示を生成"""
        
        instructions = {
            "start": [
                {"to": "narrator", "emotion": "neutral", "length": "medium", "sample": None},
            ],
            "too_long": [
                {"to": "critic", "emotion": "dismissive", "length": "short", "sample": "で？"},
                {"to": "critic", "emotion": "tired", "length": "short", "sample": "長い"},
            ],
            "too_short": [
                {"to": "narrator", "emotion": "defensive", "length": "long", "sample": "ちょっと待てよ、説明させて"},
            ],
            "needs_variation": [
                {"to": "narrator", "emotion": "angry", "length": "short", "sample": "もういい！"},
                {"to": "critic", "emotion": "sarcastic", "length": "medium", "sample": "素晴らしいね（皮肉）"},
            ],
            "normal": [
                {"to": "narrator", "emotion": "defensive", "length": "medium", "sample": None},
                {"to": "critic", "emotion": "dismissive", "length": "short", "sample": "つまらない"},
            ]
        }
        
        return random.choice(instructions.get(state, instructions["normal"]))
    
    def run_dialogue(self, theme: str, turns: int = 5):
        """改善版対話実行"""
        console.print(Panel(f"[bold green]テーマ: {theme}[/bold green]", expand=False))
        
        # 初回：語り担当がシンプルに始める
        console.print("\n[bold magenta]【語り】[/bold magenta]")
        narrator_prompt = f"次のテーマで物語を始めてください（2-3文で）: {theme}"
        narrator_response = self.get_response('narrator', narrator_prompt)
        console.print(f"{Fore.MAGENTA}{narrator_response}{Style.RESET_ALL}")
        self.conversation_history.append({'role': 'narrator', 'content': narrator_response})
        
        for turn in range(turns):
            self.turn_count = turn
            
            # 批評担当の応答
            console.print("\n[bold cyan]【批評】[/bold cyan]")
            
            # 状態分析
            state = self.analyze_conversation_state()
            instruction = self.generate_director_instruction(state)
            
            # 批評向けの指示があれば適用
            if instruction['to'] == 'critic':
                critic_prompt = f"次を批評して: {narrator_response}"
                if instruction['sample']:
                    critic_prompt = f"「{instruction['sample']}」という感じで批評: {narrator_response}"
            else:
                critic_prompt = f"短く批評して: {narrator_response}"
            
            critic_response = self.get_response('critic', critic_prompt, instruction)
            console.print(f"{Fore.CYAN}{critic_response}{Style.RESET_ALL}")
            self.conversation_history.append({'role': 'critic', 'content': critic_response})
            
            # 進行担当の介入（2ターンごと）
            if turn % 2 == 1:
                console.print("\n[dim yellow]【進行指示】[/dim yellow]")
                instruction = self.generate_director_instruction("needs_variation")
                console.print(f"[dim]{json.dumps(instruction, ensure_ascii=False)}[/dim]")
            
            # 語り担当の反応
            console.print("\n[bold magenta]【語り】[/bold magenta]")
            
            if instruction['to'] == 'narrator':
                narrator_prompt = f"批評「{critic_response}」に対して、{instruction.get('emotion', 'defensive')}に応答"
                if instruction['sample']:
                    narrator_prompt += f"。「{instruction['sample']}」から始めて"
            else:
                narrator_prompt = f"批評「{critic_response}」に短く反論"
            
            narrator_response = self.get_response('narrator', narrator_prompt, instruction)
            console.print(f"{Fore.MAGENTA}{narrator_response}{Style.RESET_ALL}")
            self.conversation_history.append({'role': 'narrator', 'content': narrator_response})
            
            console.print("-" * 50)
        
        return self.conversation_history

# ===== メイン実行 =====
def main():
    console.print("[bold green]🎭 Gemma3 対話システム - 改善版[/bold green]\n")
    
    # 設定
    config = SystemConfigV2()
    
    # Ollama確認（簡略版）
    try:
        models = ollama.list()
        console.print("[green]✅ Ollama接続確認[/green]")
    except:
        console.print("[red]❌ Ollama接続失敗[/red]")
        return 1
    
    # テーマ選択
    themes = [
        "2150年の火星コロニーでの殺人事件",
        "深夜のコンビニで起きた奇妙な出来事",
        "AI が恋に落ちた日"
    ]
    
    console.print("テーマを選択:")
    for i, theme in enumerate(themes, 1):
        console.print(f"  {i}. {theme}")
    
    choice = input("\n選択 (1-3): ").strip()
    theme = themes[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= 3 else themes[0]
    
    # 対話実行
    system = ImprovedDialogueSystem(config)
    history = system.run_dialogue(theme, turns=3)
    
    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"outputs/improved_{timestamp}.json"
    
    os.makedirs("outputs", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'theme': theme,
            'config': {
                'temperature_narrator': config.temperature_narrator,
                'temperature_critic': config.temperature_critic,
                'max_tokens': config.max_tokens_narrator
            },
            'conversation': history
        }, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n[green]✅ 保存完了: {output_file}[/green]")
    
    # GPU状態
    console.print("\n[cyan]GPU状態:[/cyan]")
    os.system("nvidia-smi --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits")
    
    return 0

if __name__ == "__main__":
    main()