import requests
import json
import os
import sys

# Configuration - Update these with your actual AWS API Gateway URL
BASE_URL = os.getenv("ORDER_SERVICE_BASE_URL")  # Change to your deployment URL (e.g., https://<api-id>.execute-api.<region>.amazonaws.com)

def test_create_order():
    print("--- Testing Create Order ---")
    url = f"{BASE_URL}/tenants/tenant123/orders"
    payload = {
        "customerName": "John Doe",
        "items": [
            {"productId": "p1", "quantity": 2, "price": 10.5},
            {"productId": "p2", "quantity": 1, "price": 5.0}
        ],
        "totalAmount": 26.0,
        "source": "WEB"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_get_order(order_id: str):
    print(f"\n--- Testing Get Order ({order_id}) ---")
    url = f"{BASE_URL}/tenants/tenant123/orders/{order_id}"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_update_order_status(order_id: str):
    url = f"{BASE_URL}/tenants/tenant123/orders/{order_id}/status"
    payload = {
        "status": "COCINA",
        "responsable": "Chef Juan",
        "taskToken": "mock-token-123"
    }
    print(f"\n--- Testing Update Order Status to COCINA ---")
    try:
        response = requests.patch(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Note: You need to replace the order_id in test_get_order and test_update_order_status 
    # with the ID returned by test_create_order if running sequentially.
    test_create_order()
    # Manual step: Update the IDs below after seeing the output of createOrder
    # test_get_order("d8a9a166-9c5e-4f76-9bdd-7ff4a3598dc4")
    # test_update_order_status("d8a9a166-9c5e-4f76-9bdd-7ff4a3598dc4")
