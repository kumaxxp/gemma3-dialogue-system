#!/usr/bin/env python3
"""
ユーティリティ関数群
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Any

import ollama
from rich.console import Console

console = Console()


def clean_response(text: str, role: str) -> str:
    """応答のクリーニング
    
    Args:
        text: クリーニング対象のテキスト
        role: 役割（"narrator" or "critic"）
    
    Returns:
        クリーニング済みのテキスト
    """
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
            "確かに",
            "という質問",
            "という指摘",
            "という疑問",
            "に対する答え",
            "に答える"
        ]
        for phrase in meta_phrases:
            text = text.replace(phrase, "")
    
    # 空白の正規化
    text = ' '.join(text.split())
    text = text.strip()
    
    return text


def check_ollama() -> bool:
    """Ollama接続確認
    
    Returns:
        接続可能な場合True、そうでない場合False
    """
    try:
        models_response = ollama.list()
        return True
    except:
        return False


def save_dialogue(dialogue: List[Dict], theme: str, analysis: Dict) -> str:
    """対話結果を保存
    
    Args:
        dialogue: 対話履歴のリスト
        theme: 対話のテーマ
        analysis: 分析結果の辞書
    
    Returns:
        保存したファイルのパス
    """
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