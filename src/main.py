#!/usr/bin/env python3
"""
エントリーポイントとUI
"""

import sys
import json
import ollama
from rich.console import Console
from colorama import init

from dialogue_system import DialogueSystem, check_ollama, save_dialogue

init(autoreset=True)
console = Console()


def check_models():
    """必要なモデルの確認"""
    try:
        # Ollama接続確認
        if not check_ollama():
            console.print("[red]❌ Ollamaに接続できません[/red]")
            console.print("\n[yellow]対処法:[/yellow]")
            console.print("  1. Ollamaが起動しているか確認:")
            console.print("     sudo systemctl status ollama")
            console.print("  2. Ollamaを起動:")
            console.print("     sudo systemctl start ollama")
            return False
        
        console.print("[green]✅ Ollama接続OK[/green]")
        
        # 必要なモデルの確認
        models_response = ollama.list()
        available_models = []
        
        if hasattr(models_response, 'models'):
            for model in models_response.models:
                if hasattr(model, 'model'):
                    available_models.append(model.model)
        
        has_4b = any("gemma3:4b" in m for m in available_models)
        has_12b = any("gemma3:12b" in m for m in available_models)
        
        if not has_4b:
            console.print("[red]❌ Gemma3:4b が見つかりません[/red]")
            console.print("以下を実行してください:")
            console.print("  ollama pull gemma3:4b")
            return False
        
        console.print("[green]✅ Gemma3:4b 検出[/green]")
        
        if not has_12b:
            console.print("[yellow]⚠️ Gemma3:12b が見つかりません（オプション）[/yellow]")
            console.print("[dim]プロンプト生成に4Bモデルを使用します[/dim]")
            # config.jsonの設定を更新
            try:
                with open("config.json", 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["models"]["prompt_generator"]["model"] = "gemma3:4b"
                with open("config.json", 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except:
                pass
        else:
            console.print("[green]✅ Gemma3:12b 検出[/green]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ エラー: {e}[/red]")
        return False


def select_theme():
    """テーマ選択"""
    # config.jsonからテーマリストを読み込む
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            themes = config.get("theme_list", [])
    except:
        # フォールバック
        themes = [
            "火星コロニーで発見された謎の信号",
            "深夜のコンビニに現れた透明人間",
            "AIロボットが見た初めての夢"
        ]
    
    themes.append("カスタム（自由入力）")
    
    console.print("\n[bold]テーマを選択してください:[/bold]")
    for i, theme in enumerate(themes, 1):
        console.print(f"  {i}. {theme}")
    
    try:
        choice = input(f"\n選択 (1-{len(themes)}): ").strip()
        idx = int(choice) - 1
        
        if idx == len(themes) - 1:  # カスタム
            selected_theme = input("テーマを入力: ").strip()
            if not selected_theme:
                selected_theme = themes[0]
        else:
            selected_theme = themes[idx]
            
    except (ValueError, IndexError):
        selected_theme = themes[0]
        console.print(f"[yellow]デフォルト選択: {selected_theme}[/yellow]")
    
    return selected_theme


def main():
    """メイン処理"""
    console.print("[bold green]🎭 Gemma3 対話システム（リファクタリング版）[/bold green]")
    console.print("[dim]A5000 + Ubuntu 24.04 最適化版[/dim]\n")
    
    # モデル確認
    if not check_models():
        return 1
    
    # テーマ選択
    selected_theme = select_theme()
    console.print(f"\n[bold cyan]選択されたテーマ: {selected_theme}[/bold cyan]\n")
    
    try:
        # 対話システム実行
        system = DialogueSystem(selected_theme, "config.json")
        dialogue = system.run_dialogue(max_turns=8)
        
        # 分析
        analysis = system.analyze_dialogue()
        
        # 結果表示
        console.print(f"\n[bold green]📊 対話分析:[/bold green]")
        console.print(f"総ターン数: {analysis['total_turns']}")
        console.print(f"矛盾指摘数: {analysis['contradiction_count']}")
        console.print(f"批評パターン: {analysis['patterns']}")
        console.print(f"平均文字数:")
        console.print(f"  語り手: {analysis['avg_length']['narrator']:.1f}文字")
        console.print(f"  批評者: {analysis['avg_length']['critic']:.1f}文字")
        
        # 保存
        filename = save_dialogue(dialogue, selected_theme, analysis)
        console.print(f"\n[green]✅ 保存完了: {filename}[/green]")
        
        # パフォーマンス情報
        console.print("\n[dim]━━━ Performance Info ━━━[/dim]")
        console.print("[dim]Models: Gemma3 4B/12B[/dim]")
        console.print("[dim]GPU: NVIDIA RTX A5000 (24GB)[/dim]")
        
        return 0
        
    except FileNotFoundError:
        console.print("[red]❌ config.jsonが見つかりません[/red]")
        console.print("上記のconfig.jsonファイルを作成してください")
        return 1
        
    except Exception as e:
        console.print(f"[red]❌ エラーが発生しました: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())