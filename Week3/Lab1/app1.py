from flask import Flask, request, jsonify

app = Flask(__name__)

posts = []
next_id = 1


# Lấy danh sách bài viết
@app.get('/api/v1/posts')
def get_posts():
    return jsonify(posts), 200


# Tạo bài viết mới
@app.post('/api/v1/posts')
def create_post():
    global next_id
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify(error='Body phải là JSON object'), 400

    title = data.get('title')
    body = data.get('body')
    author_id = data.get('author_id')

    if not title or not body or not author_id:
        return jsonify(error='Thiếu title, body hoặc author_id'), 422

    post = {
        'id': next_id,
        'title': title,
        'body': body,
        'author_id': author_id,
        'tag_ids': data.get('tag_ids', [])
    }
    posts.append(post)
    next_id += 1

    return jsonify(post), 201
