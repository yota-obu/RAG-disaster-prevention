from flask import Flask, request, jsonify
from .rag_logic import query_rag, initialize_rag_components # Import RAG functions

app = Flask(__name__)

# Initialize RAG components when the Flask app starts
# Errors during RAG init will be logged by rag_logic.py
initialize_rag_components()

import csv
import os

# Basic chat processing state
is_processing_chat = False

# AGE_CATEGORIES defines the keys for quantity_per_person_per_day
AGE_CATEGORIES = ["adult", "child", "infant", "elderly"]
STOCKPILE_ITEMS = []

# Path for docker if `data` is copied or mounted to `/app/data`
CONTAINER_CSV_PATH = '/app/data/stockpile_items.csv'

def load_stockpile_data():
    global STOCKPILE_ITEMS
    temp_items = []
    
    # Ensure AGE_CATEGORIES is accessible here if defined globally or passed as argument
    # For simplicity, assuming AGE_CATEGORIES is global or accessible in this scope.

    try:
        with open(CONTAINER_CSV_PATH, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                item = {
                    "id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "unit": row["unit"],
                }
                # Check for qty_family_once first, as it's exclusive of per-person quantities
                if row.get("qty_family_once") and row["qty_family_once"].strip():
                    try:
                        item["quantity_per_family_once"] = float(row["qty_family_once"])
                    except ValueError:
                        print(f"Warning: Could not parse qty_family_once '{row['qty_family_once']}' for item '{row['id']}' as float. Skipping item.")
                        continue # Skip this item or handle error appropriately
                else:
                    item["quantity_per_person_per_day"] = {}
                    has_any_person_qty = False
                    for cat_key in AGE_CATEGORIES: # e.g. "adult", "child"
                        col_name = f"qty_{cat_key}" # e.g. "qty_adult"
                        if row.get(col_name) and row[col_name].strip():
                            try:
                                item["quantity_per_person_per_day"][cat_key] = float(row[col_name])
                                has_any_person_qty = True
                            except ValueError:
                                print(f"Warning: Could not parse {col_name} '{row[col_name]}' for item '{row['id']}' as float. Defaulting to 0 for this category.")
                                item["quantity_per_person_per_day"][cat_key] = 0
                        else:
                            # Default to 0 if data is missing/blank for a specific age category for a per-person item
                            item["quantity_per_person_per_day"][cat_key] = 0 
                    
                    # If it wasn't a family_once item, but had no valid per-person quantities, it's ambiguous.
                    # For now, we'll add it if it had at least one per-person quantity, or it's a family_once item.
                    # This check might need refinement based on how strictly data must conform.
                    if not has_any_person_qty and not item.get("quantity_per_family_once"):
                         print(f"Warning: Item '{row['id']}' has no 'qty_family_once' and no valid per-person quantities. It might not be processed correctly in calculations.")
                
                temp_items.append(item)
        
        STOCKPILE_ITEMS = temp_items
        if not STOCKPILE_ITEMS:
            app.logger.warning("Stockpile data is empty after loading CSV. Calculations might yield no results.")
        else:
            app.logger.info(f"Successfully loaded {len(STOCKPILE_ITEMS)} items from {CONTAINER_CSV_PATH}.")
            # For debugging, print a sample of loaded items
            # app.logger.debug(f"Sample loaded items: {STOCKPILE_ITEMS[:2]}")

    except FileNotFoundError:
        app.logger.error(f"FATAL: Stockpile CSV file not found at {CONTAINER_CSV_PATH}. Stockpile functionality will be disabled.")
        STOCKPILE_ITEMS = [] # Ensure it's empty so simulator knows no data
    except Exception as e:
        app.logger.error(f"FATAL: Error loading stockpile CSV from {CONTAINER_CSV_PATH}: {e}. Stockpile functionality will be disabled.")
        STOCKPILE_ITEMS = []

# Load data when the module is imported (i.e., when Flask app starts)
load_stockpile_data()


@app.route('/api/stockpile_simulator', methods=['POST'])
def stockpile_simulator():
    # Check if STOCKPILE_ITEMS is empty and inform client if so
    if not STOCKPILE_ITEMS:
        return jsonify({"error": "Stockpile data is not available. Please check server configuration."}), 503

    data = request.get_json()
    if not data or 'family_members' not in data:
        return jsonify({"error": "Missing family_members data"}), 400

    family_members_input = data['family_members'] # e.g., {"adult": 2, "child": 1}

    # Validate input categories
    for category in family_members_input.keys():
        if category not in AGE_CATEGORIES:
            return jsonify({"error": f"Invalid family member category: {category}"}), 400

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
            if total_persons > 0:
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
        return jsonify({"error": "Previous request still processing. Please wait."}), 429 # Too Many Requests

    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    question = data['question']
    if not question.strip():
        return jsonify({"error": "Question cannot be empty"}), 400

    is_processing_chat = True
    try:
        # Call the RAG query function
        response = query_rag(question)
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error in RAG query: {e}")
        is_processing_chat = False # Reset state on error
        return jsonify({"error": "An internal error occurred while processing your question."}), 500
    finally:
        is_processing_chat = False
        
    return jsonify(response)

if __name__ == '__main__':
    # Note: When running with Flask's development server (app.run()), 
    # and debug=True, the server might reload, potentially re-running initializations.
    # For production, a WSGI server like Gunicorn would be used.
    # initialize_rag_components() is already called at module import of rag_logic
    app.run(debug=True, host='0.0.0.0', port=5001)
