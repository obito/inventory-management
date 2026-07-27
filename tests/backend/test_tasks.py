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
            "due_date": "2026-08-01"
        })
        assert response.status_code == 201

        task = response.json()
        assert task["title"] == "Review Q4 stock levels"
        assert task["priority"] == "high"
        assert task["due_date"] == "2026-08-01"
        assert task["status"] == "pending"
        assert "id" in task

    def test_create_task_defaults_priority(self, client):
        """Test that priority defaults to medium when omitted."""
        response = client.post("/api/tasks", json={
            "title": "Restock connectors",
            "due_date": "2026-08-05"
        })
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_create_task_requires_title(self, client):
        """Test that a task without a title is rejected."""
        response = client.post("/api/tasks", json={"due_date": "2026-08-05"})
        assert response.status_code == 422

    def test_created_task_appears_in_list(self, client):
        """Test that a created task is returned by the list endpoint."""
        created = client.post("/api/tasks", json={
            "title": "Audit London warehouse",
            "priority": "low",
            "due_date": "2026-08-10"
        }).json()

        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created["id"]

    def test_tasks_returned_newest_first(self, client):
        """Test that tasks are listed with the most recent first."""
        client.post("/api/tasks", json={"title": "First", "due_date": "2026-08-01"})
        client.post("/api/tasks", json={"title": "Second", "due_date": "2026-08-02"})

        data = client.get("/api/tasks").json()
        assert [t["title"] for t in data] == ["Second", "First"]

    def test_toggle_task(self, client):
        """Test toggling a task between pending and completed."""
        task_id = client.post("/api/tasks", json={
            "title": "Confirm supplier pricing",
            "due_date": "2026-08-03"
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
            "due_date": "2026-08-04"
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


class TestTaskFieldValidation:
    """Constrained fields reject bad input at the API boundary."""

    def test_create_task_rejects_unknown_priority(self, client):
        """Test that a priority outside the allowed set is a 422, not a stored value."""
        response = client.post("/api/tasks", json={
            "title": "Bad priority",
            "priority": "banana",
            "due_date": "2026-09-01"
        })
        assert response.status_code == 422

    def test_create_task_accepts_each_valid_priority(self, client):
        """Test that every documented priority is accepted."""
        for priority in ["high", "medium", "low"]:
            response = client.post("/api/tasks", json={
                "title": f"Task {priority}",
                "priority": priority,
                "due_date": "2026-09-01"
            })
            assert response.status_code == 201
            assert response.json()["priority"] == priority

    def test_create_task_defaults_priority_to_medium(self, client):
        """Test that omitting priority yields the documented default."""
        response = client.post("/api/tasks", json={
            "title": "No priority given",
            "due_date": "2026-09-02"
        })
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_created_task_uses_snake_case_due_date(self, client):
        """Test that the task payload matches the snake_case convention of the API."""
        response = client.post("/api/tasks", json={
            "title": "Naming check",
            "due_date": "2026-09-03"
        })
        assert response.status_code == 201

        task = response.json()
        assert task["due_date"] == "2026-09-03"
        assert "dueDate" not in task
