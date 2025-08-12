#!/usr/bin/env python3
"""
Gemma3 強化版対話システム
進行役が各ターンで積極的に介入し、対話のリズムと展開を制御
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import ollama
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

init(autoreset=True)
console = Console()

class ActiveDirector:
    """各ターンで具体的な指示を出す進行役"""
    
    def __init__(self):
        self.story_pace = "normal"
        self.tension_level = 0
        self.last_length = 0
        self.turn_history = []
        
    def analyze_situation(self, turn: int, dialogue_history: List[Dict]) -> Dict:
        """現在の状況を分析して次の指示を決定"""
        
        # 直前の発話を分析
        if dialogue_history:
            last_entry = dialogue_history[-1]
            last_content = last_entry["content"]
            last_length = len(last_content)
            
            # リズムの判定（長短を交互に）
            if last_length < 30:
                next_style = "detailed"  # 短い後は詳細に
                length_guidance = "3-4文"
            elif last_length > 120:
                next_style = "brief"     # 長い後は簡潔に
                length_guidance = "1文"
            else:
                next_style = "moderate"  # 適度に
                length_guidance = "2文"
        else:
            next_style = "opening"
            length_guidance = "2-3文"
            
        # ターンタイプの決定
        turn_type = self._determine_turn_type(turn)
        
        # フォーカスの決定
        focus = self._determine_focus(turn, dialogue_history)
        
        return {
            "style": next_style,
            "length": length_guidance,
            "turn_type": turn_type,
            "focus": focus,
            "turn": turn
        }
    
    def _determine_turn_type(self, turn: int) -> str:
        """ターンに応じた展開タイプを決定"""
        if turn < 2:
            return "establishing"  # 設定確立
        elif turn < 5:
            return "developing"    # 展開
        elif turn < 7:
            return "complicating"  # 複雑化・転換
        else:
            return "resolving"     # 収束へ
    
    def _determine_focus(self, turn: int, history: List[Dict]) -> str:
        """このターンで注目すべき要素を決定"""
        focus_progression = [
            "setting",      # 舞台設定
            "character",    # 人物・存在
            "mystery",      # 謎・疑問
            "discovery",    # 発見・気づき
            "conflict",     # 葛藤・問題
            "revelation",   # 真相・核心
            "resolution"    # 解決・結末
        ]
        
        # ターン数に応じて進行
        index = min(turn // 2, len(focus_progression) - 1)
        return focus_progression[index]
    
    def create_narrator_instruction(self, 
                                   critic_text: str, 
                                   situation: Dict,
                                   theme: str) -> str:
        """語り手への具体的な指示を生成"""
        
        instructions = []
        
        # 基本の長さ指示
        instructions.append(f"【長さ】{situation['length']}で語る")
        
        # 展開タイプ別の指示
        if situation["turn_type"] == "establishing":
            instructions.append("【展開】舞台と状況を明確に描写")
            if situation["turn"] == 0:
                instructions.append("【開始】印象的な出だしで始める")
        elif situation["turn_type"] == "developing":
            instructions.append("【展開】物語を前に進める。新しい情報を追加")
        elif situation["turn_type"] == "complicating":
            instructions.append("【展開】予想外の要素や転換点を入れる")
        else:
            instructions.append("【展開】クライマックスに向けて収束させる")
        
        # フォーカス指示
        focus_instructions = {
            "setting": "場所や環境の詳細",
            "character": "登場する人物や存在",
            "mystery": "謎や不可解な要素",
            "discovery": "新たな発見や気づき",
            "conflict": "困難や対立",
            "revelation": "重要な真実",
            "resolution": "結末への道筋"
        }
        instructions.append(f"【焦点】{focus_instructions[situation['focus']]}を描く")
        
        # 批評への対応指示
        if critic_text:
            if "？" in critic_text:
                instructions.append("【応答】質問に答えながら展開")
            elif len(critic_text) < 10:
                instructions.append("【応答】相槌を受けて詳しく説明")
            else:
                instructions.append("【応答】指摘を活かして発展")
        
        return "\n".join(instructions)
    
    def create_critic_instruction(self,
                                 narrator_text: str,
                                 situation: Dict) -> str:
        """批評への具体的な指示を生成"""
        
        instructions = []
        
        # リズムに応じた長さ
        if situation["style"] == "detailed":
            instructions.append("【長さ】5-10文字の短い反応")
        elif situation["style"] == "brief":
            instructions.append("【長さ】15-25文字で具体的に")
        else:
            instructions.append("【長さ】10-15文字で適度に")
        
        # 展開タイプ別の批評スタイル
        if situation["turn_type"] == "establishing":
            instructions.append("【態度】興味を示し、詳細を引き出す")
            instructions.append("【例】へー、どんな？、それで？")
        elif situation["turn_type"] == "developing":
            instructions.append("【態度】深掘りする質問で発展させる")
            instructions.append("【例】なぜ？、どうやって？、誰が？")
        elif situation["turn_type"] == "complicating":
            instructions.append("【態度】核心に迫る疑問を投げかける")
            instructions.append("【例】本当に？、他には？、つまり？")
        else:
            instructions.append("【態度】結論に向けて確認する")
            instructions.append("【例】結局？、それで？、意味は？")
        
        # 内容への反応指示
        if len(narrator_text) > 100:
            instructions.append("【反応】要点を確認する短い質問")
        elif "、" in narrator_text and narrator_text.count("、") > 2:
            instructions.append("【反応】複雑な内容を整理する質問")
        else:
            instructions.append("【反応】次を促す反応")
        
        return "\n".join(instructions)


class EnhancedLLMSystem:
    """進行役が細かく制御する対話システム"""
    
    def __init__(self, theme: str):
        self.theme = theme
        self.dialogue = []
        self.director = ActiveDirector()
        self.turn = 0
        
        # テーマ別の背景知識
        self.theme_context = self._get_theme_context(theme)
    
    def _get_theme_context(self, theme: str) -> str:
        """テーマに応じた背景知識を設定"""
        if "火星" in theme:
            return """火星の環境：
- 大気は薄い（地球の1%）
- 平均気温-60℃
- 液体の水は存在しない
- 重力は地球の38%
- 砂嵐が発生する"""
        elif "コンビニ" in theme:
            return """深夜のコンビニ：
- 24時間営業
- 少ない客
- 蛍光灯の白い光
- 静かな店内
- 防犯カメラ"""
        else:
            return """AIロボット：
- 感情シミュレーション
- 学習能力
- 物理的制約
- 電源依存
- プログラムの限界"""
    
    def clean_response(self, text: str) -> str:
        """応答をクリーン化"""
        # メタ発言を削除
        meta_phrases = [
            "承知しました", "理解しました", "わかりました",
            "はい、", "確かに", "なるほど",
            "【", "】", "（", "）"
        ]
        
        for phrase in meta_phrases:
            text = text.replace(phrase, "")
        
        # 改行と空白を整理
        text = " ".join(text.split())
        text = text.strip()
        
        return text
    
    def get_narrator_response(self,
                            critic_text: str = "",
                            director_instruction: str = "") -> str:
        """進行役の指示を受けた語り手の応答"""
        
        # プロンプト構築
        system_prompt = f"""あなたは{self.theme}の物語を語る語り手です。
{self.theme_context}

進行役の指示に正確に従って物語を語ってください。
メタ的な発言は避け、物語の世界に没入して語ってください。"""
        
        user_prompt = f"""{self.theme}の物語を続ける。

{"批評: " + critic_text if critic_text else "【物語の開始】"}

進行役からの指示：
{director_instruction}

上記の指示を守り、自然な物語として語る。"""
        
        # Ollama APIを呼び出し
        try:
            response = ollama.chat(
                model='gemma3:4b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                options={
                    'temperature': 0.7,
                    'num_predict': 150,
                    'top_p': 0.9
                }
            )
            
            # レスポンスから内容を取得
            if isinstance(response, dict) and 'message' in response:
                content = response['message']['content']
                return self.clean_response(content)
            else:
                console.print("[red]予期しない応答形式[/red]")
                return "..."
                
        except Exception as e:
            console.print(f"[red]語り手エラー: {e}[/red]")
            return "..."
    
    def get_critic_response(self,
                          narrator_text: str,
                          director_instruction: str = "") -> str:
        """進行役の指示を受けた批評の応答"""
        
        system_prompt = f"""あなたは物語の批評家です。
物語を建設的に発展させる質問や反応をします。
皮肉や悪意は不要。対話を豊かにすることが目的。
{self.theme_context}"""
        
        user_prompt = f"""語り: {narrator_text}

進行役からの指示：
{director_instruction}

指示に従い、物語を発展させる反応をする。"""
        
        try:
            response = ollama.chat(
                model='gemma3:4b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                options={
                    'temperature': 0.6,
                    'num_predict': 50,
                    'top_p': 0.8
                }
            )
            
            if isinstance(response, dict) and 'message' in response:
                content = response['message']['content']
                content = self.clean_response(content)
                
                # 長さ制限
                if len(content) > 30:
                    if '？' in content:
                        content = content.split('？')[0] + '？'
                    elif '。' in content:
                        content = content.split('。')[0] + '。'
                    else:
                        content = content[:25]
                
                return content
            else:
                return "..."
                
        except Exception as e:
            console.print(f"[red]批評エラー: {e}[/red]")
            return "..."
    
    def run_dialogue(self, max_turns: int = 10):
        """進行役が細かく制御する対話を実行"""
        
        console.print(Panel(
            f"[bold cyan]🎬 {self.theme}[/bold cyan]\n"
            f"[dim]進行役が各ターンを積極的に制御[/dim]",
            expand=False
        ))
        console.print()
        
        narrator_text = ""
        critic_text = ""
        
        for turn in range(max_turns):
            self.turn = turn
            
            # 進行役が状況を分析
            situation = self.director.analyze_situation(turn, self.dialogue)
            
            # 進行役の判断を表示
            console.print(f"[dim yellow]📢 進行役: ターン{turn+1} "
                        f"[{situation['turn_type']}] "
                        f"スタイル:{situation['style']} "
                        f"焦点:{situation['focus']}[/dim]")
            
            # 語り手のターン（偶数ターンまたは開始時）
            if turn == 0 or (turn > 0 and self.dialogue[-1]["role"] == "critic"):
                instruction = self.director.create_narrator_instruction(
                    critic_text, situation, self.theme
                )
                
                # デバッグ用：指示を表示
                if turn < 3:  # 最初の数ターンだけ詳細表示
                    console.print(f"[dim]→ 語り手への指示:\n{instruction}[/dim]")
                
                narrator_text = self.get_narrator_response(critic_text, instruction)
                
                if narrator_text and narrator_text != "...":
                    print(f"{Fore.MAGENTA}語り:{Style.RESET_ALL} {narrator_text}")
                    self.dialogue.append({
                        "role": "narrator",
                        "content": narrator_text,
                        "turn": turn,
                        "instruction_summary": situation
                    })
            
            # 批評のターン（語り手の後、最終ターン以外）
            if turn < max_turns - 1 and self.dialogue and self.dialogue[-1]["role"] == "narrator":
                instruction = self.director.create_critic_instruction(
                    narrator_text, situation
                )
                
                # デバッグ用：指示を表示
                if turn < 3:
                    console.print(f"[dim]→ 批評への指示:\n{instruction}[/dim]")
                
                critic_text = self.get_critic_response(narrator_text, instruction)
                
                if critic_text and critic_text != "...":
                    print(f"{Fore.CYAN}批評:{Style.RESET_ALL} {critic_text}")
                    self.dialogue.append({
                        "role": "critic",
                        "content": critic_text,
                        "turn": turn,
                        "instruction_summary": situation
                    })
            
            print("-" * 50)
            time.sleep(0.5)  # 読みやすさのための小休止
        
        return self.dialogue
    
    def analyze_dialogue(self) -> Dict:
        """生成された対話を分析"""
        analysis = {
            "total_turns": len(self.dialogue),
            "narrator_turns": sum(1 for d in self.dialogue if d["role"] == "narrator"),
            "critic_turns": sum(1 for d in self.dialogue if d["role"] == "critic"),
            "avg_narrator_length": 0,
            "avg_critic_length": 0,
            "rhythm_changes": 0
        }
        
        narrator_lengths = [len(d["content"]) for d in self.dialogue if d["role"] == "narrator"]
        critic_lengths = [len(d["content"]) for d in self.dialogue if d["role"] == "critic"]
        
        if narrator_lengths:
            analysis["avg_narrator_length"] = sum(narrator_lengths) / len(narrator_lengths)
        if critic_lengths:
            analysis["avg_critic_length"] = sum(critic_lengths) / len(critic_lengths)
        
        # リズムの変化を計測
        for i in range(1, len(self.dialogue)):
            prev_len = len(self.dialogue[i-1]["content"])
            curr_len = len(self.dialogue[i]["content"])
            if abs(prev_len - curr_len) > 30:
                analysis["rhythm_changes"] += 1
        
        return analysis


def check_ollama_connection():
    """Ollamaの接続とモデルの確認"""
    try:
        # まず接続を確認
        models_response = ollama.list()
        console.print("[green]✅ Ollama接続成功[/green]")
        
        # モデル一覧を取得（複数の形式に対応）
        model_names = []
        try:
            # ListResponseが直接イテレート可能な場合
            for model in models_response:
                if hasattr(model, 'name'):
                    model_names.append(model.name)
                elif isinstance(model, dict) and 'name' in model:
                    model_names.append(model['name'])
        except:
            pass
        
        if model_names:
            console.print(f"[dim]利用可能モデル: {', '.join(model_names)}[/dim]")
        
        # gemma3:4bを直接テスト
        try:
            test_response = ollama.chat(
                model='gemma3:4b',
                messages=[{'role': 'user', 'content': 'test'}],
                options={'num_predict': 1}
            )
            console.print("[green]✅ gemma3:4b 利用可能[/green]")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                console.print("[yellow]⚠️ gemma3:4bが見つかりません[/yellow]")
                console.print("[dim]インストール: ollama pull gemma3:4b[/dim]")
            else:
                console.print(f"[yellow]⚠️ gemma3:4b テストエラー: {e}[/yellow]")
            
            # 代替モデルを提案
            if model_names:
                console.print(f"[dim]利用可能なモデル: {', '.join(model_names[:3])}[/dim]")
            return False
            
    except Exception as e:
        console.print(f"[red]❌ Ollama接続エラー: {e}[/red]")
        console.print("[dim]Ollamaが起動していることを確認してください:[/dim]")
        console.print("[dim]systemctl status ollama または ollama serve[/dim]")
        return False


def main():
    """メイン実行関数"""
    console.print("[bold green]🎭 Gemma3 強化版対話システム[/bold green]")
    console.print("[dim]進行役が各ターンを積極的に制御[/dim]\n")
    
    # Ollama接続確認
    if not check_ollama_connection():
        return 1
    
    # テーマ選択
    themes = [
        "火星コロニーで発見された謎の信号",
        "深夜のコンビニに現れた透明人間",
        "AIロボットが見た初めての夢"
    ]
    
    console.print("\n[bold]テーマを選択してください:[/bold]")
    for i, theme in enumerate(themes, 1):
        console.print(f"  {i}. {theme}")
    
    try:
        choice = input("\n選択 (1-3): ").strip()
        theme_index = int(choice) - 1
        if 0 <= theme_index < len(themes):
            selected_theme = themes[theme_index]
        else:
            selected_theme = themes[0]
    except:
        selected_theme = themes[0]
    
    console.print(f"\n[green]選択されたテーマ: {selected_theme}[/green]\n")
    
    # システム実行
    system = EnhancedLLMSystem(selected_theme)
    
    try:
        dialogue = system.run_dialogue(max_turns=8)
        
        # 分析結果を表示
        console.print("\n[bold green]📊 対話分析結果[/bold green]")
        analysis = system.analyze_dialogue()
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("項目", style="dim")
        table.add_column("値", justify="right")
        
        table.add_row("総ターン数", str(analysis["total_turns"]))
        table.add_row("語り手発言数", str(analysis["narrator_turns"]))
        table.add_row("批評発言数", str(analysis["critic_turns"]))
        table.add_row("語り手平均文字数", f"{analysis['avg_narrator_length']:.1f}")
        table.add_row("批評平均文字数", f"{analysis['avg_critic_length']:.1f}")
        table.add_row("リズム変化回数", str(analysis["rhythm_changes"]))
        
        console.print(table)
        
        # ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("outputs", exist_ok=True)
        filename = f"outputs/enhanced_{timestamp}.json"
        
        output_data = {
            'theme': selected_theme,
            'dialogue': dialogue,
            'analysis': analysis,
            'timestamp': timestamp
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n[green]✅ 保存完了: {filename}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]中断されました[/yellow]")
        return 0
    except Exception as e:
        console.print(f"\n[red]エラーが発生しました: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())