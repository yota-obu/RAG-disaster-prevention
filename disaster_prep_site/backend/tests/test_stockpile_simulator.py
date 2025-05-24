import json
import pytest
from backend.app.main import app # Assuming main.py is in backend/app

# Sample data to be used for mocking STOCKPILE_ITEMS during tests
# Note: The actual app uses AGE_CATEGORIES ["adult", "child", "infant", "elderly"]
# The MOCK_STOCKPILE_ITEMS should align with these categories for quantity_per_person_per_day
MOCK_STOCKPILE_ITEMS = [
    {"id": "water", "name": "Water", "category": "food", "unit": "liters", "quantity_per_person_per_day": {"adult": 3, "child": 2, "infant": 1, "elderly": 3}},
    {"id": "emergency_food", "name": "Emergency Food", "category": "food", "unit": "servings", "quantity_per_person_per_day": {"adult": 3, "child": 3, "infant": 2, "elderly": 3}},
    {"id": "flashlight", "name": "Flashlight", "category": "essentials", "unit": "sets", "quantity_per_family_once": 1},
    {"id": "radio", "name": "Radio", "category": "essentials", "unit": "sets", "quantity_per_family_once": 1},
    # Example per-person essential, "batteries", with varied consumption
    {"id": "batteries", "name": "Batteries", "category": "essentials", "unit": "packs", "quantity_per_person_per_day": {"adult": 0.1, "child": 0.1, "infant": 0, "elderly": 0.1}}
]

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # No need to patch STOCKPILE_ITEMS directly in the fixture if monkeypatch is used in each test.
    # This also avoids issues with app context not being fully set up when patching directly on app.
    with app.test_client() as client:
        yield client

def test_stockpile_simulator_no_family(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {}})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    
    # Verify per-family items are present
    flashlight = next((item for item in data if item['id'] == 'flashlight'), None)
    assert flashlight is not None
    assert flashlight['minimum_quantity'] == 1 # Flashlight is per-family

    # Verify per-person items have 0 quantity
    water = next((item for item in data if item['id'] == 'water'), None)
    assert water is not None
    assert water['minimum_quantity'] == 0
    assert water['recommended_quantity'] == 0

    batteries = next((item for item in data if item['id'] == 'batteries'), None)
    assert batteries is not None
    assert batteries['minimum_quantity'] == 0
    assert batteries['recommended_quantity'] == 0


def test_stockpile_simulator_single_adult(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {'adult': 1}})
    assert response.status_code == 200
    data = json.loads(response.data)
    
    water = next(item for item in data if item['id'] == 'water')
    assert water['minimum_quantity'] == 3 * 3 # 3 liters/day * 3 days
    assert water['recommended_quantity'] == 3 * 7 # 3 liters/day * 7 days
    
    flashlight = next(item for item in data if item['id'] == 'flashlight')
    assert flashlight['minimum_quantity'] == 1
    assert flashlight['recommended_quantity'] == 1

    batteries = next(item for item in data if item['id'] == 'batteries')
    assert batteries['minimum_quantity'] == round(0.1 * 3, 2) # 0.1 packs/day * 3 days
    assert batteries['recommended_quantity'] == round(0.1 * 7, 2) # 0.1 packs/day * 7 days


def test_stockpile_simulator_mixed_family(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    # Using AGE_CATEGORIES from backend.app.main for consistency
    from backend.app.main import AGE_CATEGORIES
    payload = {'family_members': {'adult': 2, 'child': 1, 'infant': 1, 'elderly': 0}} # Ensure all categories in AGE_CATEGORIES are handled
    
    # Check if all keys in payload are valid according to AGE_CATEGORIES
    for key in payload['family_members']:
        assert key in AGE_CATEGORIES, f"Test payload includes invalid key: {key}"

    response = client.post('/api/stockpile_simulator', json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Water: (2 adults * 3L) + (1 child * 2L) + (1 infant * 1L) = 6 + 2 + 1 = 9L per day
    water = next(item for item in data if item['id'] == 'water')
    assert water['minimum_quantity'] == round(9 * 3, 2)
    assert water['recommended_quantity'] == round(9 * 7, 2)

    # Emergency Food: (2 adults * 3) + (1 child * 3) + (1 infant * 2) = 6 + 3 + 2 = 11 servings/day
    emergency_food = next(item for item in data if item['id'] == 'emergency_food')
    assert emergency_food['minimum_quantity'] == round(11 * 3, 2)
    assert emergency_food['recommended_quantity'] == round(11 * 7, 2)

    # Flashlight (per family)
    flashlight = next(item for item in data if item['id'] == 'flashlight')
    assert flashlight['minimum_quantity'] == 1
    assert flashlight['recommended_quantity'] == 1
    
    # Batteries (per person)
    # (2 adults * 0.1) + (1 child * 0.1) + (1 infant * 0) = 0.2 + 0.1 + 0 = 0.3 packs/day
    batteries = next(item for item in data if item['id'] == 'batteries')
    assert batteries['minimum_quantity'] == round(0.3 * 3, 2)
    assert batteries['recommended_quantity'] == round(0.3 * 7, 2)


def test_stockpile_simulator_missing_family_members_field(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={}) # Missing 'family_members' field
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    # This error message comes from the `main.py` logic
    assert data['error'] == "Missing family_members data"

def test_stockpile_simulator_family_members_not_dict(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': "not_a_dictionary"})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
     # This error message comes from the `main.py` logic (it's the same for missing or wrong type)
    assert data['error'] == "Missing family_members data"


def test_stockpile_simulator_invalid_category(client, monkeypatch):
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', MOCK_STOCKPILE_ITEMS)
    response = client.post('/api/stockpile_simulator', json={'family_members': {'alien': 1, 'adult': 1}})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert "Invalid family member category: alien" in data['error'] # Error message from main.py

def test_stockpile_simulator_data_not_loaded(client, monkeypatch):
    # Test the case where STOCKPILE_ITEMS is empty (e.g., CSV loading failed)
    monkeypatch.setattr('backend.app.main.STOCKPILE_ITEMS', [])
    response = client.post('/api/stockpile_simulator', json={'family_members': {'adult': 1}})
    assert response.status_code == 503  # Service Unavailable
    data = json.loads(response.data)
    assert 'error' in data
    # This error message comes from main.py when STOCKPILE_ITEMS is empty
    assert data['error'] == "Stockpile data is not available. Please check server configuration."
