#!/usr/bin/env python3
"""
Ollama環境診断スクリプト
接続とモデルの状態を確認
"""

import sys
import json
import subprocess
from typing import Dict, List, Any

try:
    import ollama
    print("✅ ollamaパッケージ: インポート成功")
except ImportError:
    print("❌ ollamaパッケージ: 未インストール")
    print("   実行: pip install ollama")
    sys.exit(1)

def check_ollama_service() -> bool:
    """Ollamaサービスの状態確認"""
    print("\n=== Ollamaサービス確認 ===")
    
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "ollama"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip() == "active":
            print("✅ Ollamaサービス: 稼働中")
            return True
        else:
            print(f"⚠️ Ollamaサービス: {result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"⚠️ サービス確認失敗: {e}")
        return False

def check_ollama_connection() -> bool:
    """Ollama APIへの接続確認"""
    print("\n=== Ollama API接続確認 ===")
    
    try:
        # curlでの確認
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Ollama" in result.stdout or result.returncode == 0:
            print("✅ API接続: http://localhost:11434")
        else:
            print("⚠️ API接続: 応答なし")
    except:
        print("⚠️ curlテスト失敗")
    
    return True

def check_models() -> Dict[str, Any]:
    """モデルリストの確認"""
    print("\n=== モデル確認 ===")
    
    models_info = {
        "method": None,
        "models": [],
        "raw_response": None
    }
    
    # 方法1: ollama.list()を試す
    try:
        response = ollama.list()
        models_info["raw_response"] = str(type(response))
        
        print(f"ollama.list()の返り値型: {type(response)}")
        
        # 様々な形式に対応
        if isinstance(response, dict):
            print(f"  キー: {list(response.keys())}")
            
            # 'models'キーがある場合
            if 'models' in response:
                models_info["method"] = "dict with 'models' key"
                for model in response['models']:
                    if isinstance(model, dict):
                        name = model.get('name', 'unknown')
                        models_info["models"].append(name)
                        print(f"  - {name}")
            # 直接モデル情報が入っている場合
            else:
                models_info["method"] = "dict without 'models' key"
                print(f"  内容: {json.dumps(response, indent=2, default=str)[:500]}")
        
        elif isinstance(response, list):
            models_info["method"] = "list"
            for item in response:
                if isinstance(item, dict):
                    name = item.get('name', str(item))
                    models_info["models"].append(name)
                    print(f"  - {name}")
                else:
                    models_info["models"].append(str(item))
                    print(f"  - {item}")
        
        else:
            models_info["method"] = f"unknown type: {type(response)}"
            print(f"  予期しない型: {response}")
            
    except Exception as e:
        print(f"❌ ollama.list()エラー: {e}")
        models_info["method"] = f"error: {e}"
    
    # 方法2: CLIコマンドを試す
    print("\n--- CLIでの確認 ---")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("CLI出力:")
            lines = result.stdout.strip().split('\n')
            for line in lines[:10]:  # 最初の10行
                print(f"  {line}")
            
            # モデル名を抽出（通常は2行目以降）
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    if model_name not in models_info["models"]:
                        models_info["models"].append(f"[CLI] {model_name}")
        else:
            print(f"⚠️ CLIエラー: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️ CLI確認失敗: {e}")
    
    return models_info

def test_gemma3() -> bool:
    """Gemma3モデルのテスト"""
    print("\n=== Gemma3動作テスト ===")
    
    models_to_test = ["gemma3:4b", "gemma3", "gemma2:2b"]  # フォールバック
    
    for model in models_to_test:
        print(f"\nテスト: {model}")
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "user", "content": "Say 'OK' in one word"}
                ],
                options={
                    "num_predict": 5,
                    "temperature": 0.1
                }
            )
            
            if response and 'message' in response:
                content = response['message'].get('content', '')
                print(f"✅ {model}: 動作確認OK")
                print(f"   応答: {content[:50]}")
                return True
            else:
                print(f"⚠️ {model}: 応答形式が不正")
                
        except Exception as e:
            print(f"❌ {model}: {str(e)[:100]}")
    
    return False

def print_summary(models_info: Dict[str, Any], gemma_ok: bool):
    """診断結果のサマリー"""
    print("\n" + "="*50)
    print("診断結果サマリー")
    print("="*50)
    
    if models_info["models"]:
        print(f"✅ 検出されたモデル数: {len(models_info['models'])}")
        
        gemma_models = [m for m in models_info["models"] if 'gemma' in m.lower()]
        if gemma_models:
            print(f"✅ Gemmaモデル: {', '.join(gemma_models)}")
        else:
            print("⚠️ Gemmaモデルが見つかりません")
            print("\n推奨アクション:")
            print("  ollama pull gemma3:4b")
    else:
        print("❌ モデルが検出できません")
        print("\n推奨アクション:")
        print("  1. ollama list で確認")
        print("  2. ollama pull gemma3:4b")
    
    if gemma_ok:
        print("\n✅ Gemma3は動作可能です")
    else:
        print("\n⚠️ Gemma3の動作確認ができません")
    
    print("\n詳細情報:")
    print(f"  検出方法: {models_info['method']}")
    print(f"  応答型: {models_info['raw_response']}")

def main():
    print("🔍 Ollama環境診断ツール")
    print("="*50)
    
    # 1. サービス確認
    service_ok = check_ollama_service()
    
    if not service_ok:
        print("\n💡 Ollamaを起動してください:")
        print("   sudo systemctl start ollama")
        print("   または")
        print("   ollama serve")
    
    # 2. 接続確認
    check_ollama_connection()
    
    # 3. モデル確認
    models_info = check_models()
    
    # 4. Gemma3テスト
    gemma_ok = test_gemma3()
    
    # 5. サマリー
    print_summary(models_info, gemma_ok)
    
    # 終了コード
    if gemma_ok:
        print("\n✅ 診断完了: 問題なし")
        return 0
    else:
        print("\n⚠️ 診断完了: 要対処")
        return 1

if __name__ == "__main__":
    sys.exit(main())