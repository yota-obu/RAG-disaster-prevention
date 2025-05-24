from flask import Flask, request, jsonify
from .rag_logic import query_rag, initialize_rag_components # Import RAG functions

app = Flask(__name__)

# Initialize RAG components when the Flask app starts
# Errors during RAG init will be logged by rag_logic.py
initialize_rag_components()

import csv
import os

# チャット処理中フラグ
is_processing_chat = False

# AGE_CATEGORIES は quantity_per_person_per_day のキーを定義します
AGE_CATEGORIES = ["adult", "child", "infant", "elderly"]
STOCKPILE_ITEMS = []

# Dockerコンテナ内のCSVファイルパス (dataディレクトリが /app/data にマウントまたはコピーされる場合)
CONTAINER_CSV_PATH = '/app/data/stockpile_items.csv'

def load_stockpile_data():
    global STOCKPILE_ITEMS
    temp_items = []
    
    # AGE_CATEGORIES はグローバルに定義されているか、引数として渡されることを想定

    try:
        with open(CONTAINER_CSV_PATH, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                item = {
                    "id": row["ID"], # CSVヘッダー変更に対応
                    "name": row["品目名"], # CSVヘッダー変更に対応
                    "category": row["カテゴリ"], # CSVヘッダー変更に対応
                    "unit": row["単位"], # CSVヘッダー変更に対応
                }
                # まず family_once の数量を確認 (個人別の数量とは排他的)
                if row.get("数量_家族あたり") and row["数量_家族あたり"].strip():
                    try:
                        item["quantity_per_family_once"] = float(row["数量_家族あたり"])
                    except ValueError:
                        app.logger.warning(f"警告: アイテム '{row['ID']}' の '数量_家族あたり' ('{row['数量_家族あたり']}') を数値として解析できませんでした。このアイテムをスキップします。")
                        continue # このアイテムをスキップするか、適切にエラー処理
                else:
                    item["quantity_per_person_per_day"] = {}
                    has_any_person_qty = False
                    for cat_key in AGE_CATEGORIES: # 例: "adult", "child"
                        col_name = f"数量_{cat_key}" # 例: "数量_adult"
                        if row.get(col_name) and row[col_name].strip():
                            try:
                                item["quantity_per_person_per_day"][cat_key] = float(row[col_name])
                                has_any_person_qty = True
                            except ValueError:
                                app.logger.warning(f"警告: アイテム '{row['ID']}' の '{col_name}' ('{row[col_name]}') を数値として解析できませんでした。このカテゴリのデフォルト値は0になります。")
                                item["quantity_per_person_per_day"][cat_key] = 0
                        else:
                            # 個人別アイテムで特定の年齢カテゴリのデータが欠落または空白の場合、デフォルトで0とする
                            item["quantity_per_person_per_day"][cat_key] = 0 
                    
                    if not has_any_person_qty and not item.get("quantity_per_family_once"):
                         app.logger.warning(f"警告: アイテム '{row['ID']}' には家族向け数量がなく、有効な個人別の数量もありません。計算時に正しく処理されない可能性があります。")
                
                temp_items.append(item)
        
        STOCKPILE_ITEMS = temp_items
        if not STOCKPILE_ITEMS:
            app.logger.warning("CSV読み込み後、備蓄データが空です。計算結果が得られない可能性があります。")
        else:
            app.logger.info(f"{CONTAINER_CSV_PATH} から {len(STOCKPILE_ITEMS)} 件のアイテムを正常に読み込みました。")
            # デバッグ用に読み込まれたアイテムのサンプルを出力
            # app.logger.debug(f"読み込みアイテムサンプル: {STOCKPILE_ITEMS[:2]}")

    except FileNotFoundError:
        app.logger.error(f"致命的エラー: 備蓄CSVファイルが {CONTAINER_CSV_PATH} で見つかりません。備蓄シミュレータ機能は無効になります。")
        STOCKPILE_ITEMS = [] # シミュレータにデータがないことを知らせるために空にする
    except Exception as e:
        app.logger.error(f"致命的エラー: {CONTAINER_CSV_PATH} からの備蓄CSVファイルの読み込み中にエラーが発生しました: {e}。備蓄シミュレータ機能は無効になります。")
        STOCKPILE_ITEMS = []

# モジュールインポート時 (Flaskアプリ起動時) にデータを読み込む
load_stockpile_data()


@app.route('/api/stockpile_simulator', methods=['POST'])
def stockpile_simulator():
    # STOCKPILE_ITEMSが空の場合、クライアントに通知
    if not STOCKPILE_ITEMS:
        return jsonify({"error": "備蓄データが利用できません。サーバーの設定を確認してください。"}), 503

    data = request.get_json()
    if not data or 'family_members' not in data:
        return jsonify({"error": "家族構成データが見つかりません。"}), 400

    family_members_input = data['family_members'] # 例: {"adult": 2, "child": 1}

    # 入力カテゴリの検証
    for category in family_members_input.keys():
        if category not in AGE_CATEGORIES:
            return jsonify({"error": f"無効な家族構成カテゴリです: {category}"}), 400

    results = []
    total_persons = sum(family_members_input.values())

    for item in STOCKPILE_ITEMS:
        daily_total_for_item = 0
        
        if "quantity_per_person_per_day" in item:
            for category, count in family_members_input.items():
                if count > 0 and category in item["quantity_per_person_per_day"]:
                    daily_total_for_item += item["quantity_per_person_per_day"][category] * count
            
            results.append({
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "unit": item["unit"],
                "minimum_quantity": round(daily_total_for_item * 3, 2),
                "recommended_quantity": round(daily_total_for_item * 7, 2),
            })
        elif "quantity_per_family_once" in item:
            if total_persons > 0: # 家族が一人もいない場合は家族向けアイテムも不要
                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "category": item["category"],
                    "unit": item["unit"],
                    "minimum_quantity": item["quantity_per_family_once"],
                    "recommended_quantity": item["quantity_per_family_once"],
                })
                continue

    return jsonify(results)

@app.route('/api/chat', methods=['POST'])
def chat_with_rag():
    global is_processing_chat
    
    if is_processing_chat:
        return jsonify({"error": "前のリクエストを処理中です。しばらくお待ちください。"}), 429 # Too Many Requests

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "リクエストボディに 'question' が見つかりません。"}), 400

    question = data['question']
    if not question.strip():
        return jsonify({"error": "質問内容は空にできません。"}), 400

    is_processing_chat = True
    try:
        # RAGクエリ関数を呼び出し
        response = query_rag(question)
    except Exception as e:
        # デバッグ用に例外をログに記録
        app.logger.error(f"RAGクエリでエラーが発生しました: {e}")
        is_processing_chat = False # エラー時に状態をリセット
        return jsonify({"error": "質問の処理中に内部エラーが発生しました。"}), 500
    finally:
        is_processing_chat = False
        
    return jsonify(response)

if __name__ == '__main__':
    # 注意: Flask開発サーバー (app.run()) で debug=True の場合、
    # サーバーがリロードされ、初期化が再実行される可能性があります。
    # 本番環境ではGunicornのようなWSGIサーバーを使用します。
    # initialize_rag_components() は rag_logic のモジュールインポート時に既に呼び出されています。
    app.run(debug=True, host='0.0.0.0', port=5001)
