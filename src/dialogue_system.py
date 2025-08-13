#!/usr/bin/env python3
"""
リファクタリング版：対話システムのコアロジック
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import ollama
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class DialogueSystem:
    """統合された対話システム"""
    
    def __init__(self, theme: str, config_path: str = "config.json"):
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
    
    def run_dialogue(self, max_turns: int = 10):
        """対話の実行"""
        from rich.panel import Panel
        from colorama import Fore, Style
        
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
        """語り手の応答"""
        templates = self.config["prompts"]["narrator_templates"]
        
        if self.turn == 0:
            prompt = templates["start"].format(theme=self.theme)
        elif "ない" in critic_text or "おかしい" in critic_text:
            prompt = templates["contradiction_response"].format(critic_text=critic_text)
        elif action == "breakthrough":
            prompt = templates["breakthrough"]
        elif action == "develop":
            prompt = templates["develop"]
        elif action == "climax":
            prompt = templates["climax"]
        else:
            prompt = templates["continue"].format(critic_text=critic_text)
        
        messages = [
            {"role": "system", "content": f"あなたは「{self.theme}」の物語を語る語り手です。簡潔に、具体的に。"},
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
        """批評の応答"""
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


class PromptGenerator:
    """プロンプト生成器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.cache = {}
    
    def get_context(self, theme: str) -> Dict[str, Any]:
        """テーマに応じたコンテキスト取得"""
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
        """動的にコンテキストを生成"""
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
        """フォールバック用の汎用コンテキスト"""
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
        
        return f"""
### 役割
あなたは{context.get('personality', '懐疑的')}な批評家です。

### ルール
1. 返答は必ず15文字以内
2. 最初は短い相槌（へー、ふーん、続けて）
3. 矛盾を見つけたら具体的に指摘
4. 質問は簡潔に（どこで？いつ？なぜ？）

### この物語の重要な事実
{facts}

### 存在してはいけないもの
{forbidden}

### 指摘の例
- 「{forbidden.split(',')[0] if forbidden else '矛盾'}はない」
- 「それはおかしい。{forbidden}」
- 「ありえない。{forbidden}」
"""


class SmartDirector:
    """進行管理"""
    
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


# ユーティリティ関数
def clean_response(text: str, role: str) -> str:
    """応答のクリーニング"""
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


def check_ollama() -> bool:
    """Ollama接続確認"""
    try:
        models_response = ollama.list()
        return True
    except:
        return False


def save_dialogue(dialogue: List[Dict], theme: str, analysis: Dict) -> str:
    """対話結果を保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/dialogue_{timestamp}.json"
    
    save_data = {
        "theme": theme,
        "dialogue": dialogue,
        "analysis": analysis,
        "timestamp": timestamp
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    return filename