import json
import pytest
from backend.app.main import app # main.py が backend/app にあると仮定

# テスト中にSTOCKPILE_ITEMSをモック化するために使用するサンプルデータ
# 注意: 実際のアプリは AGE_CATEGORIES ["adult", "child", "infant", "elderly"] を使用する
# MOCK_STOCKPILE_ITEMS は quantity_per_person_per_day についてこれらのカテゴリと整合している必要がある
MOCK_STOCKPILE_ITEMS = [
    {"id": "water", "name": "Water", "category": "food", "unit": "liters", "quantity_per_person_per_day": {"adult": 3, "child": 2, "infant": 1, "elderly": 3}},
    {"id": "emergency_food", "name": "Emergency Food", "category": "food", "unit": "servings", "quantity_per_person_per_day": {"adult": 3, "child": 3, "infant": 2, "elderly": 3}},
    {"id": "flashlight", "name": "Flashlight", "category": "essentials", "unit": "sets", "quantity_per_family_once": 1},
    {"id": "radio", "name": "Radio", "category": "essentials", "unit": "sets", "quantity_per_family_once": 1},
    # 個人ごとの必需品の例、「batteries」、消費量は様々
    {"id": "batteries", "name": "Batteries", "category": "essentials", "unit": "packs", "quantity_per_person_per_day": {"adult": 0.1, "child": 0.1, "infant": 0, "elderly": 0.1}}
]

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # 各テストでmonkeypatchを使用する場合、フィクスチャで直接STOCKPILE_ITEMSをパッチする必要はない
    # これにより、アプリのコンテキストが完全に設定されていない場合にアプリに直接パッチを適用する際の問題も回避できる
    with app.test_client() as client:
        yield client

def test_stockpile_simulator_no_family(client, monkeypatch):
    """
    家族構成が空の場合の備蓄シミュレータの動作を検証します。
    このシナリオでは、家族向けアイテム（例: 懐中電灯）は基本量が返され、
    個人向けアイテム（例: 水、電池）は消費がないため0が返されることを期待します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {}})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    
    # 家族向けアイテムが存在することを確認
    flashlight = next((item for item in data if item['id'] == 'flashlight'), None)
    assert flashlight is not None
    assert flashlight['minimum_quantity'] == 1 # 懐中電灯は家族向け

    # 個人向けアイテムの数量が0であることを確認
    water = next((item for item in data if item['id'] == 'water'), None)
    assert water is not None
    assert water['minimum_quantity'] == 0
    assert water['recommended_quantity'] == 0

    batteries = next((item for item in data if item['id'] == 'batteries'), None)
    assert batteries is not None
    assert batteries['minimum_quantity'] == 0
    assert batteries['recommended_quantity'] == 0


def test_stockpile_simulator_single_adult(client, monkeypatch):
    """
    家族構成が大人1人の場合の備蓄シミュレータの動作を検証します。
    大人1人分の消費量に基づいて、各個人向けアイテムの最低備蓄量（3日分）と
    推奨備蓄量（7日分）が正しく計算されることを確認します。
    家族向けアイテムは基本量が返されることを期待します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {'adult': 1}})
    assert response.status_code == 200
    data = json.loads(response.data)
    
    water = next(item for item in data if item['id'] == 'water')
    assert water['minimum_quantity'] == 3 * 3 # 1日3リットル * 3日分
    assert water['recommended_quantity'] == 3 * 7 # 1日3リットル * 7日分
    
    flashlight = next(item for item in data if item['id'] == 'flashlight')
    assert flashlight['minimum_quantity'] == 1
    assert flashlight['recommended_quantity'] == 1

    batteries = next(item for item in data if item['id'] == 'batteries')
    assert batteries['minimum_quantity'] == round(0.1 * 3, 2) # 1日0.1パック * 3日分
    assert batteries['recommended_quantity'] == round(0.1 * 7, 2) # 1日0.1パック * 7日分


def test_stockpile_simulator_mixed_family(client, monkeypatch):
    """
    複数の年齢層（大人2人、子供1人、乳児1人）が混在する家族構成の場合の
    備蓄シミュレータの動作を検証します。
    各年齢層の消費量に基づいて、個人向けアイテムの合計備蓄量が正しく計算されること、
    および家族向けアイテムが基本量で返されることを確認します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    # 一貫性のために backend.app.main から AGE_CATEGORIES を使用
    from backend.app.main import AGE_CATEGORIES
    payload = {'family_members': {'adult': 2, 'child': 1, 'infant': 1, 'elderly': 0}} # AGE_CATEGORIES内のすべてのカテゴリが処理されることを確認
    
    # ペイロード内のすべてのキーがAGE_CATEGORIESに従って有効かどうかを確認
    for key in payload['family_members']:
        assert key in AGE_CATEGORIES, f"テストペイロードに無効なキーが含まれています: {key}"

    response = client.post('/api/stockpile_simulator', json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # 水: (大人2人 * 3L) + (子供1人 * 2L) + (乳児1人 * 1L) = 6 + 2 + 1 = 1日9L
    water = next(item for item in data if item['id'] == 'water')
    assert water['minimum_quantity'] == round(9 * 3, 2)
    assert water['recommended_quantity'] == round(9 * 7, 2)

    # 非常食: (大人2人 * 3) + (子供1人 * 3) + (乳児1人 * 2) = 6 + 3 + 2 = 1日11食分
    emergency_food = next(item for item in data if item['id'] == 'emergency_food')
    assert emergency_food['minimum_quantity'] == round(11 * 3, 2)
    assert emergency_food['recommended_quantity'] == round(11 * 7, 2)

    # 懐中電灯 (家族向け)
    flashlight = next(item for item in data if item['id'] == 'flashlight')
    assert flashlight['minimum_quantity'] == 1
    assert flashlight['recommended_quantity'] == 1
    
    # 電池 (個人向け)
    # (大人2人 * 0.1) + (子供1人 * 0.1) + (乳児1人 * 0) = 0.2 + 0.1 + 0 = 1日0.3パック
    batteries = next(item for item in data if item['id'] == 'batteries')
    assert batteries['minimum_quantity'] == round(0.3 * 3, 2)
    assert batteries['recommended_quantity'] == round(0.3 * 7, 2)


def test_stockpile_simulator_missing_family_members_field(client, monkeypatch):
    """
    APIリクエスト時に 'family_members' フィールドが欠落している場合の
    エラーハンドリングを検証します。
    ステータスコード400と、フィールド欠落を示す適切なエラーメッセージが
    返されることを期待します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={}) # 'family_members' フィールドが欠落
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    # このエラーメッセージは `main.py` のロジックから来る (日本語化されているはず)
    assert data['error'] == "家族構成データが見つかりません。" # "Missing family_members data" の日本語訳

def test_stockpile_simulator_family_members_not_dict(client, monkeypatch):
    """
    APIリクエストの 'family_members' フィールドが期待される辞書型ではなく、
    不正な型（例: 文字列）で送信された場合のエラーハンドリングを検証します。
    ステータスコード400と、データ型が不適切であることを示すエラーメッセージ
    (またはフィールド欠落と同様のメッセージ) が返されることを期待します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': "not_a_dictionary"})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
     # このエラーメッセージは `main.py` のロジックから来る (欠落または間違った型の場合と同じ) (日本語化されているはず)
    assert data['error'] == "家族構成データが見つかりません。" # "Missing family_members data" の日本語訳


def test_stockpile_simulator_invalid_category(client, monkeypatch):
    """
    家族構成に無効なカテゴリキー（例: 'alien'）が含まれている場合の
    エラーハンドリングを検証します。
    ステータスコード400と、無効なカテゴリが含まれていることを示す
    適切なエラーメッセージが返されることを期待します。
    """
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {'alien': 1, 'adult': 1}})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert "無効な家族構成カテゴリです: alien" in data['error'] # main.py からのエラーメッセージ (日本語化されているはず)

def test_stockpile_simulator_data_not_loaded(client, monkeypatch):
    """
    備蓄品データ (STOCKPILE_ITEMS) が何らかの理由で空リストになっている
    （例: CSVファイルの読み込みに失敗した場合など）状況をシミュレートします。
    この場合、APIはステータスコード503（Service Unavailable）を返し、
    データが利用できない旨のエラーメッセージを返すことを期待します。
    """
    # STOCKPILE_ITEMS が空の場合 (例: CSV読み込み失敗) のテストケース
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', [])
    response = client.post('/api/stockpile_simulator', json={'family_members': {'adult': 1}})
    assert response.status_code == 503  # Service Unavailable
    data = json.loads(response.data)
    assert 'error' in data
    # このエラーメッセージは STOCKPILE_ITEMS が空の場合に main.py から来る (日本語化されているはず)
    assert data['error'] == "備蓄データが利用できません。サーバーの設定を確認してください。"
