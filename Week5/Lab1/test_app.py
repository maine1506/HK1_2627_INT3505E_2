import unittest
from app import create_app, seed
from Lab1.models import BookAuthor, Review, db


class BookstoreTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        seed()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_list_and_representation(self):
        response = self.client.get("/api/v1/books?limit=2")
        self.assertEqual(response.status_code, 200)
        body = response.json
        self.assertEqual(body["pagination"]["total"], 30)
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["data"][0]["price"]["currency"], "VND")
        self.assertTrue(body["data"][0]["authors"])
        self.assertNotIn("email", self.client.get("/api/v1/users/1").json)

    def test_book_crud_and_validation(self):
        payload = dict(title="New book", isbn="9781234567890", price_vnd=50000, stock=2, category_id=1)
        response = self.client.post("/api/v1/books", json=payload)
        self.assertEqual(response.status_code, 201)
        url = response.headers["Location"]
        self.assertEqual(self.client.post("/api/v1/books", json=payload).status_code, 409)
        payload["stock"] = 8
        self.assertEqual(self.client.put(url, json=payload).json["stock"], 8)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        for invalid in (None, [], {}, {**payload, "price_vnd": -1}, {**payload, "stock": True}):
            self.assertEqual(self.client.post("/api/v1/books", json=invalid).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/books", json={**payload, "category_id": 999}).status_code, 404)

    def test_relations_and_cascade(self):
        url = "/api/v1/books/book_1"
        self.assertEqual(self.client.post(url + "/authors", json={"author_id": 1, "role": "co"}).status_code, 201)
        self.assertEqual(self.client.post(url + "/authors", json={"author_id": 1, "role": "co"}).status_code, 409)
        self.assertEqual(self.client.delete(url + "/authors/1").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/books/book_2/reviews/1").status_code, 404)
        self.assertEqual(self.client.post(url + "/reviews", json={"rating": 6, "comment": "", "user_id": 1}).status_code, 400)
        self.assertEqual(self.client.delete("/api/v1/categories/1").status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertIsNone(db.session.get(Review, 1))
        self.assertIsNone(db.session.get(BookAuthor, (1, 2)))

    def test_other_resources_and_review_crud(self):
        for resource, payload in [
            ("authors", {"name": "C", "bio": ""}),
            ("categories", {"name": "Art", "slug": "art"}),
            ("users", {"email": "c@example.com", "display_name": "C"}),
        ]:
            response = self.client.post("/api/v1/" + resource, json=payload)
            self.assertEqual(response.status_code, 201)
            url = response.headers["Location"]
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.put(url, json=payload).status_code, 200)
            self.assertEqual(self.client.delete(url).status_code, 204)
        url = "/api/v1/books/book_2/reviews"
        payload = {"rating": 4, "comment": "Good", "user_id": 1}
        response = self.client.post(url, json=payload)
        self.assertEqual(response.status_code, 201)
        detail = url + "/" + str(response.json["id"])
        self.assertEqual(self.client.put(detail, json={**payload, "rating": 5}).json["rating"], 5)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_bad_pagination(self):
        for query in ("limit=0", "limit=abc", "offset=-1"):
            self.assertEqual(self.client.get("/api/v1/books?" + query).status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)

