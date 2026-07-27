"""
Tests for reports API endpoints and their filtering.
"""
import pytest


class TestQuarterlyReportEndpoint:
    """Test suite for /api/reports/quarterly."""

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

    def test_quarterly_reports_sorted_by_quarter(self, client):
        """Test that quarters come back in order."""
        data = client.get("/api/reports/quarterly").json()
        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that avg_order_value matches revenue / orders."""
        data = client.get("/api/reports/quarterly").json()

        for quarter in data:
            expected = quarter["total_revenue"] / quarter["total_orders"]
            assert abs(quarter["avg_order_value"] - expected) < 0.01

    def test_quarterly_fulfillment_rate_range(self, client):
        """Test that fulfillment rates are valid percentages."""
        data = client.get("/api/reports/quarterly").json()

        for quarter in data:
            assert 0 <= quarter["fulfillment_rate"] <= 100

    def test_quarterly_reports_by_warehouse(self, client):
        """Test filtering quarterly reports by warehouse."""
        response = client.get("/api/reports/quarterly?warehouse=Tokyo")
        assert response.status_code == 200

        filtered_total = sum(q["total_orders"] for q in response.json())
        tokyo_orders = len(client.get("/api/orders?warehouse=Tokyo").json())
        assert filtered_total == tokyo_orders

    def test_quarterly_reports_by_category(self, client):
        """Test filtering quarterly reports by category."""
        response = client.get("/api/reports/quarterly?category=Sensors")
        assert response.status_code == 200

        filtered_total = sum(q["total_orders"] for q in response.json())
        sensor_orders = len(client.get("/api/orders?category=Sensors").json())
        assert filtered_total == sensor_orders

    def test_quarterly_reports_by_status(self, client):
        """Test filtering quarterly reports by order status."""
        response = client.get("/api/reports/quarterly?status=Delivered")
        assert response.status_code == 200

        data = response.json()
        # Every remaining order is delivered, so fulfillment is always 100%
        for quarter in data:
            assert quarter["fulfillment_rate"] == 100.0

    def test_quarterly_reports_by_month(self, client):
        """Test filtering quarterly reports to a single month."""
        response = client.get("/api/reports/quarterly?month=2025-02")
        assert response.status_code == 200

        data = response.json()
        assert [q["quarter"] for q in data] == ["Q1-2025"]

    def test_quarterly_reports_filter_reduces_totals(self, client):
        """Test that filtering returns a subset of the unfiltered data."""
        unfiltered = sum(q["total_orders"] for q in client.get("/api/reports/quarterly").json())
        filtered = sum(
            q["total_orders"]
            for q in client.get("/api/reports/quarterly?warehouse=London").json()
        )
        assert 0 < filtered < unfiltered


class TestMonthlyTrendsEndpoint:
    """Test suite for /api/reports/monthly-trends."""

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

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that months come back in chronological order."""
        data = client.get("/api/reports/monthly-trends").json()
        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_trends_month_format(self, client):
        """Test that month keys use the YYYY-MM format."""
        data = client.get("/api/reports/monthly-trends").json()

        for entry in data:
            assert len(entry["month"]) == 7
            assert entry["month"].startswith("2025-")

    def test_monthly_trends_by_month(self, client):
        """Test filtering monthly trends to a single month."""
        response = client.get("/api/reports/monthly-trends?month=2025-03")
        assert response.status_code == 200

        data = response.json()
        assert [m["month"] for m in data] == ["2025-03"]

    def test_monthly_trends_by_warehouse(self, client):
        """Test filtering monthly trends by warehouse."""
        response = client.get("/api/reports/monthly-trends?warehouse=London")
        assert response.status_code == 200

        filtered_total = sum(m["order_count"] for m in response.json())
        london_orders = len(client.get("/api/orders?warehouse=London").json())
        assert filtered_total == london_orders

    def test_monthly_trends_multiple_filters(self, client):
        """Test combining filters on monthly trends."""
        response = client.get(
            "/api/reports/monthly-trends?warehouse=Tokyo&status=Delivered"
        )
        assert response.status_code == 200

        filtered_total = sum(m["order_count"] for m in response.json())
        expected = len(client.get("/api/orders?warehouse=Tokyo&status=Delivered").json())
        assert filtered_total == expected

    def test_monthly_trends_delivered_count_within_order_count(self, client):
        """Test that delivered orders never exceed total orders."""
        data = client.get("/api/reports/monthly-trends").json()

        for entry in data:
            assert entry["delivered_count"] <= entry["order_count"]

    def test_reports_totals_match_orders_endpoint(self, client):
        """Test that report totals agree with the raw orders data."""
        orders = client.get("/api/orders").json()
        monthly = client.get("/api/reports/monthly-trends").json()

        assert sum(m["order_count"] for m in monthly) == len(orders)
        assert abs(
            sum(m["revenue"] for m in monthly) - sum(o["total_value"] for o in orders)
        ) < 0.01


class TestCategorySpendingPercentages:
    """Test suite for derived percentages on /api/spending/categories."""

    def test_category_percentages_sum_to_100(self, client):
        """Test that category shares add up to the whole."""
        data = client.get("/api/spending/categories").json()
        assert abs(sum(c["percentage"] for c in data) - 100.0) < 0.1

    def test_category_percentages_match_amounts(self, client):
        """Test that each percentage is derived from its amount."""
        data = client.get("/api/spending/categories").json()
        total = sum(c["amount"] for c in data)

        for category in data:
            expected = round((category["amount"] / total) * 100, 1)
            assert abs(category["percentage"] - expected) < 0.01

    def test_category_percentage_ranking_matches_amount_ranking(self, client):
        """Test that a larger amount never shows a smaller share."""
        data = sorted(client.get("/api/spending/categories").json(),
                      key=lambda c: c["amount"], reverse=True)

        percentages = [c["percentage"] for c in data]
        assert percentages == sorted(percentages, reverse=True)
