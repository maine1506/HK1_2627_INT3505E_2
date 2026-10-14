from pathlib import Path
from uuid import UUID, uuid4

import yaml
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

SPEC_PATH = Path(__file__).with_name("openapi.yaml")

with SPEC_PATH.open("r", encoding="utf-8") as file:
    OPENAPI_SPEC = yaml.safe_load(file)

VALID_STATUSES = {"open", "in_progress", "completed"}

tasks = {}

def error(message, status_code):
    return jsonify({"message": message}), status_code

def validate_status(data):
    if "status" in data and data["status"] not in VALID_STATUSES:
        return "status must be open, in_progress, or completed"
    return None

def find_task(task_id):
    try:
        normalized_id = str(UUID(task_id))
    except (ValueError, AttributeError):
        return None

    return tasks.get(normalized_id)

@app.get("/v1/openapi.json")
def openapi_json():
    return jsonify(OPENAPI_SPEC)

@app.get("/docs")
def swagger_docs():
    return Response(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Tasks API - Swagger UI</title>
            <link rel="stylesheet"
              href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script>
                SwaggerUIBundle({
                    url: "/v1/openapi.json",
                    dom_id: "#swagger-ui",
                    deepLinking: true
                });
            </script>
        </body>
        </html>
        """,
        mimetype="text/html",
    )

@app.get("/v1/tasks")
def list_tasks():
    limit = request.args.get("limit", default=None, type=int)
    status = request.args.get("status")
    if request.args.get("limit") is not None:
        if limit is None or limit < 0 or limit > 100:
            return error("limit must be an integer from 0 to 100", 400)
    if status is not None and status not in VALID_STATUSES:
        return error("Invalid status", 400)
    result = list(tasks.values())
    if status is not None:
        result = [task for task in result if task["status"] == status]
    if limit is not None:
        result = result[:limit]
    return jsonify(result), 200

@app.post("/v1/tasks")
def create_task():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be a JSON object", 400)
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return error("title is required and must be a non-empty string", 400)
    status_error = validate_status(data)
    if status_error:
        return error(status_error, 400)
    task_id = str(uuid4())
    task = {
        "id": task_id,
        "title": title.strip(),
        "status": data.get("status", "open"),
    }
    tasks[task_id] = task
    return jsonify(task), 201

@app.get("/v1/tasks/<task_id>")
def get_task(task_id):
    task = find_task(task_id)
    if task is None:
        return error("Task not found", 404)
    return jsonify(task), 200

@app.patch("/v1/tasks/<task_id>")
def patch_task(task_id):
    task = find_task(task_id)
    if task is None:
        return error("Task not found", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return error("Provide a non-empty JSON object", 400)
    allowed_fields = {"title", "status"}
    if not set(data).issubset(allowed_fields):
        return error("Only title and status can be updated", 400)
    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            return error("title must be a non-empty string", 400)
    status_error = validate_status(data)
    if status_error:
        return error(status_error, 400)
    if "title" in data:
        task["title"] = data["title"].strip()
    if "status" in data:
        task["status"] = data["status"]
    return jsonify(task), 200

@app.delete("/v1/tasks/<task_id>")
def delete_task(task_id):
    task = find_task(task_id)
    if task is None:
        return error("Task not found", 404)
    del tasks[task["id"]]
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)