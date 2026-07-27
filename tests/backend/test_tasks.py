"""
Tests for tasks API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_tasks():
    """Tasks live in module-level state, so isolate each test."""
    main.tasks.clear()
    yield
    main.tasks.clear()


class TestTasksEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks_empty(self, client):
        """Test getting tasks when none have been created."""
        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_task(self, client):
        """Test creating a task."""
        response = client.post("/api/tasks", json={
            "title": "Review Q4 stock levels",
            "priority": "high",
            "dueDate": "2026-08-01"
        })
        assert response.status_code == 201

        task = response.json()
        assert task["title"] == "Review Q4 stock levels"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2026-08-01"
        assert task["status"] == "pending"
        assert "id" in task

    def test_create_task_defaults_priority(self, client):
        """Test that priority defaults to medium when omitted."""
        response = client.post("/api/tasks", json={
            "title": "Restock connectors",
            "dueDate": "2026-08-05"
        })
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_create_task_requires_title(self, client):
        """Test that a task without a title is rejected."""
        response = client.post("/api/tasks", json={"dueDate": "2026-08-05"})
        assert response.status_code == 422

    def test_created_task_appears_in_list(self, client):
        """Test that a created task is returned by the list endpoint."""
        created = client.post("/api/tasks", json={
            "title": "Audit London warehouse",
            "priority": "low",
            "dueDate": "2026-08-10"
        }).json()

        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created["id"]

    def test_tasks_returned_newest_first(self, client):
        """Test that tasks are listed with the most recent first."""
        client.post("/api/tasks", json={"title": "First", "dueDate": "2026-08-01"})
        client.post("/api/tasks", json={"title": "Second", "dueDate": "2026-08-02"})

        data = client.get("/api/tasks").json()
        assert [t["title"] for t in data] == ["Second", "First"]

    def test_toggle_task(self, client):
        """Test toggling a task between pending and completed."""
        task_id = client.post("/api/tasks", json={
            "title": "Confirm supplier pricing",
            "dueDate": "2026-08-03"
        }).json()["id"]

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        # Toggling again returns it to pending
        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_delete_task(self, client):
        """Test deleting a task."""
        task_id = client.post("/api/tasks", json={
            "title": "Archive old orders",
            "dueDate": "2026-08-04"
        }).json()["id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200

        assert client.get("/api/tasks").json() == []

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist."""
        response = client.patch("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
