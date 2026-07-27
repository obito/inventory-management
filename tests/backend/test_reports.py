"""
Tests for reports API endpoints.
"""
import pytest


class TestReportsEndpoints:
    """Test suite for reports-related endpoints."""

    # ---------- Structure ----------

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly performance reports."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "quarter" in first
        assert "total_orders" in first
        assert "total_revenue" in first
        assert "avg_order_value" in first
        assert "fulfillment_rate" in first

    def test_get_monthly_trends(self, client):
        """Test getting month-over-month trends."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "month" in first
        assert "order_count" in first
        assert "revenue" in first
        assert "delivered_count" in first

    def test_quarterly_types_and_ranges(self, client):
        """Test that quarterly numeric fields have valid types and ranges."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            assert isinstance(quarter["total_orders"], int)
            assert isinstance(quarter["total_revenue"], (int, float))
            assert isinstance(quarter["avg_order_value"], (int, float))
            assert isinstance(quarter["fulfillment_rate"], (int, float))
            assert quarter["total_orders"] > 0
            assert quarter["total_revenue"] >= 0
            assert 0 <= quarter["fulfillment_rate"] <= 100

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that monthly trends are returned in chronological order."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [m["month"] for m in data]
        assert months == sorted(months)

    # ---------- Warehouse filter ----------

    def test_quarterly_by_warehouse(self, client):
        """Test filtering quarterly reports by warehouse."""
        response = client.get("/api/reports/quarterly?warehouse=Tokyo")
        assert response.status_code == 200

        filtered = response.json()
        unfiltered = client.get("/api/reports/quarterly").json()

        filtered_orders = sum(q["total_orders"] for q in filtered)
        unfiltered_orders = sum(q["total_orders"] for q in unfiltered)

        assert filtered_orders > 0
        assert filtered_orders < unfiltered_orders

    def test_monthly_trends_by_warehouse(self, client):
        """Test filtering monthly trends by warehouse."""
        response = client.get("/api/reports/monthly-trends?warehouse=Tokyo")
        assert response.status_code == 200

        filtered = response.json()
        unfiltered = client.get("/api/reports/monthly-trends").json()

        assert sum(m["order_count"] for m in filtered) < sum(
            m["order_count"] for m in unfiltered
        )

    def test_quarterly_warehouse_matches_orders_endpoint(self, client):
        """Test that quarterly totals match the filtered orders endpoint."""
        warehouse = "San Francisco"
        orders = client.get(f"/api/orders?warehouse={warehouse}").json()
        quarterly = client.get(f"/api/reports/quarterly?warehouse={warehouse}").json()

        assert sum(q["total_orders"] for q in quarterly) == len(orders)

        expected_revenue = sum(order["total_value"] for order in orders)
        actual_revenue = sum(q["total_revenue"] for q in quarterly)
        assert abs(actual_revenue - expected_revenue) < 0.01

    # ---------- Month filter ----------

    def test_monthly_trends_by_month(self, client):
        """Test filtering monthly trends to a single month."""
        response = client.get("/api/reports/monthly-trends?month=2025-01")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-01"

    def test_quarterly_by_month_keeps_only_that_quarter(self, client):
        """Test that a January filter leaves only Q1 in quarterly reports."""
        response = client.get("/api/reports/quarterly?month=2025-01")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["quarter"] == "Q1-2025"

    def test_quarterly_by_quarter_filter(self, client):
        """Test filtering quarterly reports by a quarter value."""
        response = client.get("/api/reports/quarterly?month=Q2-2025")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["quarter"] == "Q2-2025"

    def test_monthly_trends_month_matches_orders_endpoint(self, client):
        """Test that monthly trend counts match the filtered orders endpoint."""
        orders = client.get("/api/orders?month=2025-03").json()
        trends = client.get("/api/reports/monthly-trends?month=2025-03").json()

        assert sum(m["order_count"] for m in trends) == len(orders)

    # ---------- Category and status filters ----------

    def test_quarterly_by_category(self, client):
        """Test filtering quarterly reports by category."""
        response = client.get("/api/reports/quarterly?category=sensors")
        assert response.status_code == 200

        filtered = response.json()
        unfiltered = client.get("/api/reports/quarterly").json()

        assert sum(q["total_orders"] for q in filtered) < sum(
            q["total_orders"] for q in unfiltered
        )

    def test_quarterly_by_status_delivered_is_fully_fulfilled(self, client):
        """Test that filtering to delivered orders yields a 100% fulfillment rate."""
        response = client.get("/api/reports/quarterly?status=delivered")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for quarter in data:
            assert quarter["fulfillment_rate"] == 100.0

    def test_monthly_trends_by_status(self, client):
        """Test filtering monthly trends by status."""
        response = client.get("/api/reports/monthly-trends?status=shipped")
        assert response.status_code == 200

        trends = response.json()
        orders = client.get("/api/orders?status=shipped").json()

        assert sum(m["order_count"] for m in trends) == len(orders)
        # Shipped orders are not delivered, so no month reports a delivery
        assert all(m["delivered_count"] == 0 for m in trends)

    # ---------- Combined filters ----------

    def test_quarterly_multiple_filters(self, client):
        """Test quarterly reports with multiple filters combined."""
        query = "warehouse=San Francisco&status=delivered&month=Q1-2025"
        response = client.get(f"/api/reports/quarterly?{query}")
        assert response.status_code == 200

        quarterly = response.json()
        orders = client.get(f"/api/orders?{query}").json()

        assert sum(q["total_orders"] for q in quarterly) == len(orders)
        for quarter in quarterly:
            assert quarter["quarter"] == "Q1-2025"

    def test_monthly_trends_multiple_filters(self, client):
        """Test monthly trends with multiple filters combined."""
        query = "warehouse=London&category=sensors"
        trends = client.get(f"/api/reports/monthly-trends?{query}").json()
        orders = client.get(f"/api/orders?{query}").json()

        assert sum(m["order_count"] for m in trends) == len(orders)

    # ---------- Explicit "all" behaves as no filter ----------

    def test_all_filter_value_is_ignored(self, client):
        """Test that passing 'all' is equivalent to passing no filter."""
        baseline = client.get("/api/reports/quarterly").json()
        explicit = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()

        assert explicit == baseline

    # ---------- Empty results ----------

    def test_filter_with_no_matches_returns_empty_list(self, client):
        """Test that a filter matching nothing returns an empty list, not an error."""
        response = client.get("/api/reports/quarterly?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

        response = client.get("/api/reports/monthly-trends?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    # ---------- Business logic ----------

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that avg_order_value equals total_revenue / total_orders."""
        data = client.get("/api/reports/quarterly").json()

        for quarter in data:
            expected = quarter["total_revenue"] / quarter["total_orders"]
            assert abs(quarter["avg_order_value"] - expected) < 0.01

    def test_quarterly_fulfillment_rate_calculation(self, client):
        """Test that fulfillment_rate equals delivered / total as a percentage."""
        data = client.get("/api/reports/quarterly").json()

        for quarter in data:
            expected = (quarter["delivered_orders"] / quarter["total_orders"]) * 100
            assert abs(quarter["fulfillment_rate"] - expected) < 0.1

    def test_monthly_revenue_matches_quarterly_revenue(self, client):
        """Test that monthly and quarterly revenue totals agree."""
        monthly = client.get("/api/reports/monthly-trends").json()
        quarterly = client.get("/api/reports/quarterly").json()

        monthly_total = sum(m["revenue"] for m in monthly)
        quarterly_total = sum(q["total_revenue"] for q in quarterly)

        assert abs(monthly_total - quarterly_total) < 0.01
