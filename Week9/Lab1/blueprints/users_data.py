"""In-memory single source of truth; restarting resets all changes."""

from threading import Lock

USERS = {
    1: {'first_name': 'Văn', 'last_name': 'Nguyễn', 'email': 'a@vnu.vn'},
    2: {'first_name': 'Trang', 'last_name': 'Trần', 'email': 'b@vnu.vn'},
}
_lock = Lock()


def get_user(uid):
    return USERS.get(uid)


def create_user(data):
    with _lock:
        uid = max(USERS, default=0) + 1
        USERS[uid] = dict(data)
    return {'id': uid, **data}
