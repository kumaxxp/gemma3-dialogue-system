#!/usr/bin/env python3
"""
Gemma3 Three-Role Dialogue System
Initial Setup and Test Script
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import ollama
from colorama import init, Fore, Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Colorama初期化
init(autoreset=True)
console = Console()

# ===== 設定クラス =====
@dataclass
class SystemConfig:
    """システム全体の設定"""
    ollama_host: str = "http://localhost:11434"
    model_narrator: str = "gemma3:4b"
    model_critic: str = "gemma3:4b"
    model_director: str = "gemma3:4b"
    model_analyzer: str = "gemma3:12b"  # 将来用
    
    max_tokens_narrator: int = 300
    max_tokens_critic: int = 150
    max_tokens_director: int = 100
    
    log_dir: str = "./logs"
    output_dir: str = "./outputs"
    
    # デバッグモード
    debug: bool = True
    verbose: bool = True

# ===== 基本プロンプト =====
PROMPTS = {
    "narrator": """あなたは創造的な物語の語り手です。
感情豊かに物語を語りますが、批判されると人間らしく反応します。
批評には時に感情的になり、言い訳や反論をすることもあります。
進行担当の指示（JSON形式）が来たら、その指示に従って応答してください。""",
    
    "critic": """あなたは批評家です。
必ずしも建設的でなく、時に「で？」「だから？」と短く否定することもあります。
理由なく批判したり、皮肉を言ったりすることもあります。
進行担当の指示（JSON形式）が来たら、その態度や応答スタイルに従ってください。""",
    
    "director": """あなたは会話の進行を管理する演出家です。
語りと批評の会話を観察し、自然な人間の会話になるよう調整します。
必ずJSON形式で指示を出してください。
例：{"to": "narrator", "emotion": "defensive", "style": "short", "instruction": "言い訳する"}"""
}

def test_ollama_connection(config: SystemConfig):
    """Ollama接続テスト"""
    console.print("\n[bold cyan]🔍 Ollama接続テスト開始[/bold cyan]")
    
    try:
        # モデルリスト取得
        response = ollama.list()
        
        table = Table(title="利用可能なモデル")
        table.add_column("モデル名", style="cyan")
        table.add_column("サイズ", style="green")
        table.add_column("状態", style="yellow")
        
        required_models = [config.model_narrator, config.model_critic, config.model_director]
        
        # ListResponseからモデル情報を取得
        available_models = {}
        for m in response.models:  # response.models でアクセス
            model_name = m.model  # m.name ではなく m.model
            size_gb = m.size / 1e9
            available_models[model_name] = f"{size_gb:.1f}GB"
        
        console.print(f"[dim]発見されたモデル: {list(available_models.keys())}[/dim]")
        
        # 必要なモデルの確認
        all_available = True
        for model in required_models:
            if model in available_models:
                table.add_row(model, available_models[model], "✅ 利用可能")
            else:
                table.add_row(model, "-", "❌ 未インストール")
                console.print(f"[red]モデル {model} をインストールしてください: ollama pull {model}[/red]")
                all_available = False
        
        console.print(table)
        return all_available
        
    except Exception as e:
        console.print(f"[bold red]❌ Ollama接続エラー: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False
    
# ===== 簡易会話テスト =====
class SimpleDialogueTest:
    """基本的な会話テスト"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.conversation_history = []
        
    def get_response(self, role: str, prompt: str, system_prompt: str = None):
        """単一の応答を取得"""
        try:
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            model_map = {
                'narrator': self.config.model_narrator,
                'critic': self.config.model_critic,
                'director': self.config.model_director
            }
            
            response = ollama.chat(
                model=model_map[role],
                messages=messages
            )
            
            return response['message']['content']
            
        except Exception as e:
            console.print(f"[red]エラー ({role}): {e}[/red]")
            return None
    
    def run_test_conversation(self, theme: str, turns: int = 3):
        """テスト会話を実行"""
        console.print(Panel(f"[bold green]テーマ: {theme}[/bold green]", expand=False))
        
        # 初回の語り
        console.print("\n[bold magenta]語り担当:[/bold magenta]")
        narrator_response = self.get_response(
            'narrator',
            f"次のテーマで物語を始めてください: {theme}",
            PROMPTS['narrator']
        )
        console.print(f"{Fore.MAGENTA}{narrator_response}{Style.RESET_ALL}")
        self.conversation_history.append({'role': 'narrator', 'content': narrator_response})
        
        # 批評
        console.print("\n[bold cyan]批評担当:[/bold cyan]")
        critic_response = self.get_response(
            'critic',
            f"次の語りを批評してください（時に理不尽に）:\n{narrator_response}",
            PROMPTS['critic']
        )
        console.print(f"{Fore.CYAN}{critic_response}{Style.RESET_ALL}")
        self.conversation_history.append({'role': 'critic', 'content': critic_response})
        
        # 進行担当の分析（簡易版）
        console.print("\n[bold yellow]進行担当:[/bold yellow]")
        director_instruction = self.get_director_instruction_simple()
        console.print(f"{Fore.YELLOW}{json.dumps(director_instruction, ensure_ascii=False, indent=2)}{Style.RESET_ALL}")
        
        # 指示を受けた語りの応答
        console.print("\n[bold magenta]語り担当（指示適用後）:[/bold magenta]")
        narrator_response2 = self.get_response(
            'narrator',
            f"批評: {critic_response}\n\n進行指示: {json.dumps(director_instruction)}\n\nこの指示に従って応答してください。",
            PROMPTS['narrator']
        )
        console.print(f"{Fore.MAGENTA}{narrator_response2}{Style.RESET_ALL}")
        
        return self.conversation_history
    
    def get_director_instruction_simple(self):
        """簡易的な進行指示（ルールベース）"""
        # 後でLLMベースに置き換え
        import random
        
        instructions = [
            {
                "to": "narrator",
                "emotion": "defensive",
                "style": "short",
                "instruction": "批判に対して短く言い訳する"
            },
            {
                "to": "narrator",
                "emotion": "angry",
                "style": "long",
                "instruction": "感情的に長く反論する"
            },
            {
                "to": "critic",
                "emotion": "dismissive",
                "style": "one_word",
                "instruction": "一言で切り捨てる"
            }
        ]
        
        return random.choice(instructions)

# ===== メイン実行 =====
def main():
    """メインエントリーポイント"""
    console.print("[bold green]🎭 Gemma3 Three-Role Dialogue System[/bold green]")
    console.print("[cyan]初期セットアップとテスト[/cyan]\n")
    
    # 設定読み込み
    config = SystemConfig()
    
    # Step 1: Ollama接続確認
    if not test_ollama_connection(config):
        console.print("[bold red]Ollama接続に失敗しました。環境を確認してください。[/bold red]")
        return 1
    
    # Step 2: 簡易会話テスト
    console.print("\n[bold cyan]📝 簡易会話テストを開始します[/bold cyan]")
    
    test_themes = [
        "2150年の火星コロニーでの殺人事件",
        "魔法学院での禁書発見",
        "現代東京のカフェでの奇妙な出来事"
    ]
    
    # ユーザー選択
    console.print("\nテーマを選択してください:")
    for i, theme in enumerate(test_themes, 1):
        console.print(f"  {i}. {theme}")
    
    try:
        choice = input("\n選択 (1-3): ").strip()
        theme_index = int(choice) - 1
        if 0 <= theme_index < len(test_themes):
            theme = test_themes[theme_index]
        else:
            theme = test_themes[0]
    except:
        theme = test_themes[0]
    
    # テスト実行
    tester = SimpleDialogueTest(config)
    history = tester.run_test_conversation(theme, turns=1)
    
    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{config.output_dir}/test_{timestamp}.json"
    
    os.makedirs(config.output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'theme': theme,
            'timestamp': timestamp,
            'conversation': history
        }, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n[green]✅ テスト完了！結果を保存: {output_file}[/green]")
    
    # GPU状態確認
    console.print("\n[bold cyan]📊 GPU状態確認[/bold cyan]")
    os.system("nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())