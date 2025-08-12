#!/usr/bin/env python3
"""
Gemma3 動的プロンプト生成版対話システム
テーマに応じて批評プロンプトを自動生成
"""

import os
import json
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

import ollama
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

init(autoreset=True)
console = Console()

# ===== Gemma3最適化設定 =====
GEMMA3_CONFIG = {
    "narrator": {
        "model": "gemma3:4b",
        "temperature": 0.7,
        "num_predict": 100,
        "top_p": 0.9,
        "repeat_penalty": 1.1
    },
    "critic": {
        "model": "gemma3:4b", 
        "temperature": 0.6,
        "num_predict": 40,
        "top_p": 0.85,
        "repeat_penalty": 1.2
    },
    "prompt_generator": {
        "model": "gemma3:12b",  # より賢いモデルでプロンプト生成
        "temperature": 0.3,
        "num_predict": 500,
        "top_p": 0.95
    }
}

class DynamicPromptGenerator:
    """テーマに応じた批評プロンプトの動的生成"""
    
    def __init__(self):
        self.model_config = GEMMA3_CONFIG["prompt_generator"]
        self.cache = {}  # 生成済みプロンプトのキャッシュ
        
    def extract_theme_elements(self, theme: str) -> Dict[str, str]:
        """テーマから主要要素を抽出"""
        prompt = f"""
テーマ: {theme}

このテーマから以下の要素を抽出してください。
簡潔に答えてください。

1. 舞台/場所:
2. 時代/時間:
3. 主要要素:
4. ジャンル:

JSON形式で返答:
{{"setting": "...", "time": "...", "element": "...", "genre": "..."}}
"""
        
        try:
            response = ollama.chat(
                model=self.model_config["model"],
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": 200
                }
            )
            
            content = response['message']['content']
            # JSON部分を抽出
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # フォールバック
        return {
            "setting": "不明",
            "time": "現代",
            "element": theme,
            "genre": "フィクション"
        }
    
    def generate_critic_context(self, theme: str) -> Dict[str, Any]:
        """批評用のコンテキストを生成"""
        
        # キャッシュチェック
        if theme in self.cache:
            console.print("[dim]💾 キャッシュからプロンプトを取得[/dim]")
            return self.cache[theme]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[yellow]批評プロンプト生成中...", total=None)
            
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
                response = ollama.chat(
                    model=self.model_config["model"],
                    messages=[
                        {"role": "system", "content": "あなたは物語の設定を分析する専門家です。"},
                        {"role": "user", "content": prompt}
                    ],
                    options=self.model_config
                )
                
                content = response['message']['content']
                
                # JSONを抽出（```json``` ブロックも考慮）
                content = re.sub(r'```json\n?', '', content)
                content = re.sub(r'```\n?', '', content)
                
                # JSON部分を見つける
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    self.cache[theme] = result
                    progress.stop_task(task)
                    return result
                    
            except Exception as e:
                console.print(f"[red]⚠️ プロンプト生成エラー: {e}[/red]")
            
            progress.stop_task(task)
            
        # フォールバック
        return self._get_fallback_context(theme)
    
    def _get_fallback_context(self, theme: str) -> Dict[str, Any]:
        """フォールバック用の汎用コンテキスト"""
        if "火星" in theme:
            return {
                "facts": [
                    "火星には液体の水は存在しない",
                    "大気は薄く二酸化炭素が主成分",
                    "平均気温は-60度",
                    "重力は地球の38%",
                    "砂嵐が頻繁に発生する"
                ],
                "contradictions": [
                    "雨が降る",
                    "呼吸可能な大気",
                    "豊かな植生"
                ],
                "personality": "科学的",
                "focus": ["物理法則", "技術的整合性"],
                "forbidden": ["液体の水", "生物", "酸素"]
            }
        elif "コンビニ" in theme:
            return {
                "facts": [
                    "24時間営業",
                    "狭い店内スペース",
                    "定番商品の品揃え",
                    "店員は1-2名",
                    "防犯カメラ設置"
                ],
                "contradictions": [
                    "巨大な売り場",
                    "珍しい商品",
                    "大人数の店員"
                ],
                "personality": "現実的",
                "focus": ["日常性", "リアリティ"],
                "forbidden": ["恐竜", "宇宙船", "魔法"]
            }
        else:
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
        """批評AI用のシステムプロンプトを構築"""
        
        facts = "\n".join([f"・{fact}" for fact in context.get("facts", [])])
        forbidden = ", ".join(context.get("forbidden", []))
        
        # Gemma3に最適化されたプロンプト
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
    """進行管理の改善版"""
    
    def __init__(self):
        self.contradiction_count = 0
        self.last_contradiction_turn = -1
        self.story_momentum = 0
        self.critic_patterns = []
        
    def analyze_critic_response(self, text: str) -> str:
        """批評のパターンを分析"""
        if "ない" in text or "おかしい" in text or "ありえない" in text:
            return "contradiction"
        elif "？" in text:
            return "question"
        elif len(text) <= 5:
            return "backchannel"  # 相槌
        else:
            return "comment"
    
    def get_instruction(self, turn: int, last_critic: str = "", last_narrator: str = "") -> Dict:
        """状況に応じた適切な指示"""
        
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

class DynamicDialogueSystem:
    """動的プロンプト生成による対話システム"""
    
    def __init__(self, theme: str):
        self.theme = theme
        self.dialogue = []
        self.director = SmartDirector()
        self.turn = 0
        
        # プロンプト生成
        generator = DynamicPromptGenerator()
        self.context = generator.generate_critic_context(theme)
        self.critic_prompt = generator.create_critic_prompt(self.context)
        
        # デバッグ表示
        self._show_context()
    
    def _show_context(self):
        """生成されたコンテキストを表示"""
        console.print("\n[bold cyan]📋 生成された批評設定[/bold cyan]")
        console.print(f"性格: {self.context.get('personality', '不明')}")
        console.print(f"重要事実: {len(self.context.get('facts', []))}個")
        console.print(f"禁止要素: {', '.join(self.context.get('forbidden', []))}")
        console.print()
    
    def clean_response(self, text: str, role: str) -> str:
        """応答のクリーニング（Gemma3特有のパターンに対応）"""
        
        # Gemma3が出力しやすい不要なパターンを削除
        patterns_to_remove = [
            r'\[.*?\]',  # 括弧
            r'「|」',    # 鉤括弧
            r'^はい、',  # 冒頭の「はい」
            r'^ええと、', # 冒頭の「ええと」
            r'^そうですね、', # 冒頭の「そうですね」
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text)
        
        # メタ発言の削除
        if role == "narrator":
            meta_phrases = [
                "承知しました",
                "わかりました",
                "理解しました",
                "ご指摘",
                "修正",
                "確かに"
            ]
            for phrase in meta_phrases:
                text = text.replace(phrase, "")
        
        # 空白の正規化
        text = ' '.join(text.split())
        text = text.strip()
        
        return text
    
    def get_narrator_response(self, critic_text: str = "", action: str = "continue") -> str:
        """語り手の応答（Gemma3最適化）"""
        
        # アクションに応じたプロンプト生成
        if self.turn == 0:
            prompt = f"「{self.theme}」の物語を始めてください。具体的な場面から2文で。"
        
        elif "ない" in critic_text or "おかしい" in critic_text:
            # 矛盾指摘への対応
            prompt = f"""
批評: {critic_text}

この指摘を踏まえて物語を修正し、続けてください。
メタな説明は不要。自然に物語を2文で続けてください。
"""
        
        elif action == "breakthrough":
            prompt = f"批評は無視して、物語に新しい展開を加えてください。驚きの要素を2文で。"
        
        elif action == "develop":
            prompt = f"前の内容を発展させてください。より詳細に2文で。"
        
        elif action == "climax":
            prompt = f"物語をクライマックスに導いてください。重要な発見や転機を2文で。"
        
        else:
            prompt = f"""
批評: {critic_text}

この批評を受けて物語を続けてください。2文で。
"""
        
        # Gemma3用の構造化
        messages = [
            {"role": "system", "content": f"あなたは「{self.theme}」の物語を語る語り手です。簡潔に、具体的に。"},
            {"role": "user", "content": prompt}
        ]
        
        response = ollama.chat(
            model=GEMMA3_CONFIG["narrator"]["model"],
            messages=messages,
            options=GEMMA3_CONFIG["narrator"]
        )
        
        text = self.clean_response(response['message']['content'], "narrator")
        
        # 2文制限
        sentences = re.split(r'[。！？]', text)
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) > 2:
            text = '。'.join(sentences[:2]) + '。'
        
        return text
    
    def get_critic_response(self, narrator_text: str, action: str = "listen") -> str:
        """批評の応答（Gemma3最適化）"""
        
        # アクション別プロンプト
        action_prompts = {
            "listen": "相槌を打ってください。5文字以内。（例：へー、ふーん、それで？）",
            "question": "短い質問をしてください。10文字以内。（例：どこで？なぜ？）",
            "analyze": f"矛盾があれば指摘、なければ感想。15文字以内。禁止要素: {', '.join(self.context.get('forbidden', []))}",
            "change_pattern": "いつもと違う反応をしてください。10文字以内。",
            "final_doubt": "最後の疑問や感想。15文字以内。"
        }
        
        prompt = f"""
語り手: {narrator_text}

{action_prompts.get(action, '反応してください。10文字以内。')}
"""
        
        response = ollama.chat(
            model=GEMMA3_CONFIG["critic"]["model"],
            messages=[
                {"role": "system", "content": self.critic_prompt},
                {"role": "user", "content": prompt}
            ],
            options=GEMMA3_CONFIG["critic"]
        )
        
        text = self.clean_response(response['message']['content'], "critic")
        
        # 長さ制限
        if len(text) > 20:
            # 句読点で切る
            for delimiter in ['。', '？', '！', '、']:
                if delimiter in text:
                    text = text.split(delimiter)[0] + delimiter
                    break
            else:
                text = text[:20]
        
        return text
    
    def run_dialogue(self, max_turns: int = 10):
        """対話の実行"""
        
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
    
    def analyze_dialogue(self) -> Dict[str, Any]:
        """対話の分析"""
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

def main():
    console.print("[bold green]🎭 Gemma3 動的プロンプト生成版[/bold green]")
    console.print("[dim]A5000 + Ubuntu 24.04 最適化版[/dim]\n")
    
    # Ollama確認
    try:
        # まずは単純な接続テスト
        try:
            models_response = ollama.list()
            console.print("[dim]Ollama応答確認...[/dim]")
        except Exception as conn_error:
            console.print(f"[red]❌ Ollama接続失敗: {conn_error}[/red]")
            console.print("\n[yellow]対処法:[/yellow]")
            console.print("  1. Ollamaが起動しているか確認:")
            console.print("     sudo systemctl status ollama")
            console.print("  2. Ollamaを起動:")
            console.print("     sudo systemctl start ollama")
            console.print("  3. ポート確認:")
            console.print("     curl http://localhost:11434")
            return 1
        
        # モデルリストの構造を確認
        available_models = []
        
        # ollama._types.ListResponse型に対応
        if hasattr(models_response, 'models'):
            # ListResponse型の場合（現在のollama）
            for model in models_response.models:
                if hasattr(model, 'model'):
                    # Modelオブジェクトのmodel属性から名前を取得
                    available_models.append(model.model)
                elif isinstance(model, dict) and 'name' in model:
                    available_models.append(model['name'])
                elif isinstance(model, str):
                    available_models.append(model)
        elif isinstance(models_response, dict):
            # 辞書形式の場合（旧バージョン）
            if 'models' in models_response:
                for model in models_response['models']:
                    if isinstance(model, dict) and 'name' in model:
                        available_models.append(model['name'])
                    elif isinstance(model, str):
                        available_models.append(model)
        elif isinstance(models_response, list):
            # リスト形式の場合
            for model in models_response:
                if isinstance(model, dict) and 'name' in model:
                    available_models.append(model['name'])
                elif isinstance(model, str):
                    available_models.append(model)
        
        if not available_models:
            # モデルリストが取得できない場合、直接動作確認
            console.print("[yellow]⚠️ モデルリストの取得に失敗。動作確認を試みます...[/yellow]")
            try:
                test = ollama.chat(
                    model='gemma3:4b',
                    messages=[{'role': 'user', 'content': 'test'}],
                    options={'num_predict': 1}
                )
                console.print("[green]✅ Gemma3:4b 動作確認OK[/green]")
                available_models = ['gemma3:4b']
                
                # 12Bも試す
                try:
                    test = ollama.chat(
                        model='gemma3:12b',
                        messages=[{'role': 'user', 'content': 'test'}],
                        options={'num_predict': 1}
                    )
                    available_models.append('gemma3:12b')
                except:
                    pass
            except:
                console.print("[red]❌ Gemma3:4b が動作しません[/red]")
                console.print("以下を実行してください:")
                console.print("  ollama pull gemma3:4b")
                return 1
        
        # モデル情報の表示
        console.print(f"[green]✅ Ollama接続OK[/green]")
        console.print(f"[dim]検出されたモデル: {', '.join(available_models[:3])}{'...' if len(available_models) > 3 else ''}[/dim]")
        
        # 必要なモデルのチェック
        has_4b = any("gemma3:4b" in m for m in available_models)
        has_12b = any("gemma3:12b" in m for m in available_models)
        
        if not has_4b:
            console.print("[red]❌ Gemma3:4b が見つかりません[/red]")
            console.print("以下を実行してください:")
            console.print("  ollama pull gemma3:4b")
            return 1
        
        if not has_12b:
            console.print("[yellow]⚠️ Gemma3:12b が見つかりません（オプション）[/yellow]")
            console.print("[dim]プロンプト生成に4Bモデルを使用します[/dim]")
            GEMMA3_CONFIG["prompt_generator"]["model"] = "gemma3:4b"
        else:
            console.print("[dim]12Bモデルでプロンプト生成を行います[/dim]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]❌ 予期しないエラー: {e}[/red]")
        console.print("\n[yellow]デバッグ手順:[/yellow]")
        console.print("  1. 診断スクリプトを実行:")
        console.print("     python check_ollama.py")
        console.print("  2. 手動でテスト:")
        console.print("     ollama run gemma3:4b 'Hello'")
        return 1
    
    # テーマ選択（拡張版）
    themes = [
        "火星コロニーで発見された謎の信号",
        "深夜のコンビニに現れた透明人間",
        "AIロボットが見た初めての夢",
        "江戸時代の寿司屋に現れたタイムトラベラー",
        "深海1万メートルの研究施設で起きた事件",
        "量子コンピュータの中に生まれた意識",
        "月面都市での殺人事件",
        "カスタム（自由入力）"
    ]
    
    console.print("[bold]テーマを選択してください:[/bold]")
    for i, theme in enumerate(themes, 1):
        console.print(f"  {i}. {theme}")
    
    try:
        choice = input("\n選択 (1-8): ").strip()
        idx = int(choice) - 1
        
        if idx == 7:  # カスタム
            selected_theme = input("テーマを入力: ").strip()
            if not selected_theme:
                selected_theme = themes[0]
        else:
            selected_theme = themes[idx]
            
    except (ValueError, IndexError):
        selected_theme = themes[0]
        console.print(f"[yellow]デフォルト選択: {selected_theme}[/yellow]")
    
    console.print(f"\n[bold cyan]選択されたテーマ: {selected_theme}[/bold cyan]\n")
    
    # 実行
    system = DynamicDialogueSystem(selected_theme)
    dialogue = system.run_dialogue(max_turns=8)
    
    # 分析結果表示
    analysis = system.analyze_dialogue()
    
    console.print(f"\n[bold green]📊 対話分析:[/bold green]")
    console.print(f"総ターン数: {analysis['total_turns']}")
    console.print(f"矛盾指摘数: {analysis['contradiction_count']}")
    console.print(f"批評パターン: {analysis['patterns']}")
    console.print(f"平均文字数:")
    console.print(f"  語り手: {analysis['avg_length']['narrator']:.1f}文字")
    console.print(f"  批評者: {analysis['avg_length']['critic']:.1f}文字")
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/dynamic_{timestamp}.json"
    
    save_data = {
        "theme": selected_theme,
        "context": system.context,
        "dialogue": dialogue,
        "analysis": analysis,
        "timestamp": timestamp
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n[green]✅ 保存完了: {filename}[/green]")
    
    # パフォーマンス情報
    console.print("\n[dim]━━━ Performance Info ━━━[/dim]")
    console.print("[dim]Models: Gemma3 4B (dialogue) + 12B (prompts)[/dim]")
    console.print("[dim]GPU: NVIDIA RTX A5000 (24GB)[/dim]")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())