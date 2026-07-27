"""
Tests for restocking order API endpoints.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for restocking-order-related endpoints."""

    def test_get_all_restocking_orders(self, client):
        """Test getting all submitted restocking orders."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_place_restocking_order(self, client):
        """Test submitting a restocking order with valid items."""
        response = client.get("/api/restocking-orders")
        count_before = len(response.json())

        payload = {
            "budget": 5000,
            "items": [
                {
                    "item_sku": "WDG-001",
                    "item_name": "Industrial Widget Type A",
                    "quantity": 100,
                    "unit_cost": 42.50,
                    "line_total": 4250.00
                }
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert "order_number" in data
        assert data["total_value"] == 4250.00
        assert "T" in data["expected_delivery"]
        assert "T" in data["submitted_date"]

        response = client.get("/api/restocking-orders")
        assert len(response.json()) == count_before + 1

    def test_place_restocking_order_appears_in_list(self, client):
        """Test that a submitted restocking order shows up in the GET list."""
        payload = {
            "budget": 1000,
            "items": [
                {
                    "item_sku": "GSK-203",
                    "item_name": "High-Temperature Gasket",
                    "quantity": 50,
                    "unit_cost": 15.00,
                    "line_total": 750.00
                }
            ]
        }
        create_response = client.post("/api/restocking-orders", json=payload)
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        list_response = client.get("/api/restocking-orders")
        all_ids = [order["id"] for order in list_response.json()]
        assert created_id in all_ids

    def test_place_restocking_order_empty_items_rejected(self, client):
        """Test that a restocking order with no items is rejected."""
        payload = {"budget": 1000, "items": []}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 422

    def test_place_restocking_order_missing_body_rejected(self, client):
        """Test that a restocking order request missing required fields is rejected."""
        response = client.post("/api/restocking-orders", json={})
        assert response.status_code == 422

    def test_restocking_order_total_value_calculation(self, client):
        """Test that total_value matches the sum of line totals."""
        payload = {
            "budget": 10000,
            "items": [
                {
                    "item_sku": "FLT-405",
                    "item_name": "Oil Filter Cartridge",
                    "quantity": 200,
                    "unit_cost": 8.00,
                    "line_total": 1600.00
                },
                {
                    "item_sku": "VLV-506",
                    "item_name": "Pressure Relief Valve",
                    "quantity": 30,
                    "unit_cost": 95.00,
                    "line_total": 2850.00
                }
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 200

        data = response.json()
        expected_total = sum(item["line_total"] for item in payload["items"])
        assert abs(data["total_value"] - expected_total) < 0.01

    def test_restocking_order_lead_time_is_max_of_items(self, client):
        """Test that order-level lead time equals the max lead time across its items."""
        # BRG-102 has a 7 day lead time, CTL-330 has a 30 day lead time
        payload = {
            "budget": 30000,
            "items": [
                {
                    "item_sku": "BRG-102",
                    "item_name": "Steel Bearing Assembly",
                    "quantity": 100,
                    "unit_cost": 85.00,
                    "line_total": 8500.00
                },
                {
                    "item_sku": "CTL-330",
                    "item_name": "Logic Controller Board",
                    "quantity": 50,
                    "unit_cost": 220.00,
                    "line_total": 11000.00
                }
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["lead_time_days"] == 30

    def test_restocking_order_items_structure(self, client):
        """Test that restocking order items have proper structure."""
        response = client.get("/api/restocking-orders")
        data = response.json()

        for order in data:
            assert "items" in order
            assert isinstance(order["items"], list)

            for item in order["items"]:
                assert "item_sku" in item
                assert "item_name" in item
                assert "quantity" in item
                assert "unit_cost" in item
                assert "line_total" in item
                assert isinstance(item["quantity"], int)
                assert isinstance(item["unit_cost"], (int, float))

    def test_demand_forecast_includes_pricing_fields(self, client):
        """Test that demand forecasts now include unit_cost and lead_time_days."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0

        for forecast in data:
            assert "unit_cost" in forecast
            assert "lead_time_days" in forecast
            assert isinstance(forecast["unit_cost"], (int, float))
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0
