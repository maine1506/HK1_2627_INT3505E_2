from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
import uuid
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.ERROR)

ERROR_BASE = "https://api.example.com/probs"

class ApiProblem(Exception):
    def __init__(self, status, title, detail=None, type_path=None, **extra):
        super().__init__()
        self.status = status
        self.title = title
        self.detail = detail
        self.type_path = type_path
        self.extra = extra

def _problem(status, title, detail=None, type_path=None, **extra):
    body = {
        "type": f"{ERROR_BASE}/{type_path}" if type_path else "about:blank",
        "title": title,
        "status": status,
        "instance": request.path,
        "trace_id": str(uuid.uuid4()) 
    }
    
    if detail:
        body["detail"] = detail
        
    body.update(extra)

    resp = jsonify(body)
    resp.status_code = status
    resp.headers["Content-Type"] = "application/problem+json" 
    return resp

@app.errorhandler(ApiProblem)
def handle_api_problem(e):
    return _problem(
        status=e.status,
        title=e.title,
        detail=e.detail,
        type_path=e.type_path,
        **e.extra
    )

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    # Trả về các trường tương ứng của HTTPException
    return _problem(
        status=e.code,
        title=e.name,
        detail=e.description,
        type_path="http-error"
    )

@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    logging.error(f"Unhandled Exception at {request.path}: {str(e)}", exc_info=True)
    
    return _problem(
        status=500,
        title="Internal Server Error",
        detail="Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
        type_path="internal-server-error"
    )

@app.get("/users/<int:id>")
def get_user(id):
    if id == 9999:
        raise ApiProblem(
            status=404,
            title="User not found",
            type_path="user-not-found",
            resource_id=id
        )
    return jsonify({"id": id, "name": "Nguyễn Văn A"})

