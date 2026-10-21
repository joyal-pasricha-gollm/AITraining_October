from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Task(BaseModel):
    id: int
    title: str
    status: str


tasks = [
    {
        "id": 1,
        "title": "Prepare report",
        "status": "Pending"
    },
    {
        "id": 2,
        "title": "Review invoice",
        "status": "Completed"
    },
    {
        "id": 3,
        "title": "Update dashboard",
        "status": "Pending"
    }
]


@app.get("/tasks")
def get_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):

    for task in tasks:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )


@app.post("/tasks")
def add_task(task: Task):

    tasks.append(task.dict())

    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated_task: Task):

    for index, task in enumerate(tasks):

        if task["id"] == task_id:

            tasks[index] = updated_task.dict()

            return updated_task

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):

    for task in tasks:

        if task["id"] == task_id:

            tasks.remove(task)

            return {
                "message": "Task deleted successfully"
            }

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )