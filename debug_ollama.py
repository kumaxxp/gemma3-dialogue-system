# debug_ollama.py として保存
import ollama
import json
from pprint import pprint

print("=== Ollama Debug ===")

try:
    # listメソッドの結果を確認
    result = ollama.list()
    print("\n1. ollama.list()の型:")
    print(type(result))
    
    print("\n2. ollama.list()の内容:")
    pprint(result)
    
    print("\n3. キーの確認:")
    if hasattr(result, 'keys'):
        print("Keys:", result.keys())
    
    # もしかしたら直接リストが返ってくる？
    if isinstance(result, list):
        print("\n4. リストの最初の要素:")
        if len(result) > 0:
            pprint(result[0])
            if hasattr(result[0], 'keys'):
                print("Keys in first element:", result[0].keys())
    
    # もしくはmodelsキーがある？
    if isinstance(result, dict) and 'models' in result:
        print("\n4. models の内容:")
        pprint(result['models'][:1] if result['models'] else "空のリスト")
        
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()

# 別の方法も試す
print("\n=== 別の方法 ===")
try:
    import requests
    response = requests.get('http://localhost:11434/api/tags')
    print("API Response:")
    pprint(response.json())
except Exception as e:
    print(f"requests エラー: {e}")