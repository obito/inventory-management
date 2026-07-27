"""
Tests for purchase order API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_purchase_orders():
    """Purchase orders are appended to module-level state, so isolate each test."""
    original = list(main.purchase_orders)
    main.purchase_orders.clear()
    yield
    main.purchase_orders.clear()
    main.purchase_orders.extend(original)


@pytest.fixture
def backlog_item_id(client):
    """The id of an existing backlog item."""
    return client.get("/api/backlog").json()[0]["id"]


def _payload(backlog_item_id, **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "FilterMax Inc",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2026-08-15"
    }
    payload.update(overrides)
    return payload


class TestPurchaseOrderEndpoints:
    """Test suite for purchase-order-related endpoints."""

    def test_create_purchase_order(self, client, backlog_item_id):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json=_payload(backlog_item_id))
        assert response.status_code == 201

        po = response.json()
        assert po["backlog_item_id"] == backlog_item_id
        assert po["supplier_name"] == "FilterMax Inc"
        assert po["quantity"] == 350
        assert po["unit_cost"] == 12.5
        assert po["expected_delivery_date"] == "2026-08-15"
        assert po["status"] == "Pending"
        assert po["id"].startswith("PO-")
        assert "created_date" in po

    def test_create_purchase_order_with_notes(self, client, backlog_item_id):
        """Test that optional notes are stored."""
        response = client.post(
            "/api/purchase-orders",
            json=_payload(backlog_item_id, notes="Expedite shipping")
        )
        assert response.status_code == 201
        assert response.json()["notes"] == "Expedite shipping"

    def test_get_purchase_order_by_backlog_item(self, client, backlog_item_id):
        """Test retrieving a purchase order by its backlog item id."""
        created = client.post("/api/purchase-orders", json=_payload(backlog_item_id)).json()

        response = client.get(f"/api/purchase-orders/{backlog_item_id}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_create_purchase_order_for_nonexistent_backlog_item(self, client):
        """Test creating a purchase order against an unknown backlog item."""
        response = client.post("/api/purchase-orders", json=_payload("nonexistent-999"))
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_create_duplicate_purchase_order(self, client, backlog_item_id):
        """Test that a backlog item cannot have two purchase orders."""
        client.post("/api/purchase-orders", json=_payload(backlog_item_id))

        response = client.post("/api/purchase-orders", json=_payload(backlog_item_id))
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    def test_get_nonexistent_purchase_order(self, client):
        """Test retrieving a purchase order that doesn't exist."""
        response = client.get("/api/purchase-orders/nonexistent-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "no purchase order found" in data["detail"].lower()

    def test_backlog_reflects_purchase_order_flag(self, client, backlog_item_id):
        """Test that has_purchase_order flips once a PO is raised."""
        before = client.get("/api/backlog").json()
        assert all(item["has_purchase_order"] is False for item in before)

        client.post("/api/purchase-orders", json=_payload(backlog_item_id))

        after = {item["id"]: item["has_purchase_order"] for item in client.get("/api/backlog").json()}
        assert after[backlog_item_id] is True
        assert sum(1 for flag in after.values() if flag) == 1
