from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
#Q2
def test_get_tasks():

    response = client.get("/tasks")

    assert response.status_code == 200
#Q3
def test_tasks_is_list():

    response = client.get("/tasks")

    assert isinstance(response.json(), list)
#
# #Q4
# def test_get_task_by_id():
#
#     response = client.get("/tasks/1")
#
#     assert response.status_code == 200
#
#     data = response.json()
#
#     assert data["id"] == 1

#   Q12 and 13-TESTING
def test_get_task_by_id():

    response = client.get("/tasks/1")

    data = response.json()

    assert data["title"] == "Prepare report"
#Q5:
def test_task_not_found():

    response = client.get("/tasks/999")

    assert response.status_code == 404
#Q6
def test_add_task():

    response = client.post(
        "/tasks",
        json={
            "id": 4,
            "title": "Check server logs",
            "status": "Pending"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 4
    assert data["title"] == "Check server logs"
#Q7
def test_invalid_task():

    response = client.post(
        "/tasks",
        json={
            "id": 5,
            "title": "Check Logs"
        }
    )

    assert response.status_code == 422
#Q8
def test_update_task():

    response = client.put(
        "/tasks/2",
        json={
            "id": 2,
            "title": "Review invoice",
            "status": "Completed"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Completed"
#Q9
def test_delete_task():

    response = client.delete("/tasks/3")

    assert response.status_code == 200

    assert response.json()["message"] == "Task deleted successfully"
#Q10
def test_deleted_task_not_found():

    client.delete("/tasks/3")

    response = client.get("/tasks/3")

    assert response.status_code == 404

