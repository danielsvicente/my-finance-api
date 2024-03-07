from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_account():
    balance = 1000.00

    response = client.post(
        "/accounts/",
        json={"name": "Foo Bank", "type": "CURRENT", "currency": "EUR", "balance": balance})
    data = response.json()
    assert response.status_code == 201
    assert data["name"] == "Foo Bank"
    assert "id" in data
    account_id = data["id"]

    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Foo Bank"
    assert data["id"] == account_id

    response = client.get(f"/accounts/{account_id}/history")
    assert response.status_code == 200, response.text 
    data = response.json()
    print(data)
    # assert data["account_id"] == account_id
    # assert data["balance"] == balance
    # assert data["variation"] == account_id
    # assert data["date"] == account_id

    # response = client.get(f"/accounts/total")
    # assert response.status_code == 200, response.text 
    # data = response.json()
    # assert data["balance"] == balance

    
def test_create_account_invalid_type():
    response = client.post(
        "/accounts/",
        json={"name": "Foo Bank", "type": "INVALID", "currency": "EUR", "balance": 1000.00})
    assert response.status_code == 422
