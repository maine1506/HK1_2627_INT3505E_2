import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Lab1.app import seed
from Lab1.models import Book, db
from Lab2.app import create_app
from Lab2.pagination import parse_sort, signer


class CursorTests(unittest.TestCase):
    factory = staticmethod(create_app)
    multi = False

    def setUp(self):
        self.app = self.factory({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                                 "SECRET_KEY": "test-only-key"})
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

    def page(self, **params):
        response = self.client.get("/api/v1/books", query_string=params)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def collect(self, **params):
        result = []
        for _ in range(100):
            page = self.page(**params)
            result.extend(page["data"])
            if not page["page"]["more"]:
                self.assertIsNone(page["page"]["next"])
                return result
            self.assertTrue(page["page"]["next"])
            params["cursor"] = page["page"]["next"]
        self.fail("Cursor loop did not terminate")

    def test_all_rows_no_duplicates_in_both_directions(self):
        for sort in ("id", "-id", "price", "-price"):
            with self.subTest(sort=sort):
                rows = self.collect(sort=sort, limit=4)
                keys = parse_sort(sort, self.multi)
                expected = db.session.scalars(db.select(Book).order_by(
                    *[col.desc() if desc else col.asc() for _, col, desc in keys])).all()
                self.assertEqual([r["id"] for r in rows], [f"book_{b.id}" for b in expected])
                self.assertEqual(len({r["id"] for r in rows}), 30)

    def test_filter_and_empty(self):
        rows = self.collect(category=3, sort="-price", limit=3)
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(r["category"]["id"] == 3 for r in rows))
        page = self.page(category=999)
        self.assertEqual(page["data"], [])
        self.assertFalse(page["page"]["more"])
        self.assertIsNone(page["page"]["next"])

    def test_context_and_signature_validation(self):
        token = self.page(sort="price", category=1, limit=2)["page"]["next"]
        for query in [dict(cursor=token, sort="-price", category=1),
                      dict(cursor=token, sort="price", category=2),
                      dict(cursor=token + "x", sort="price", category=1)]:
            self.assertEqual(self.client.get("/api/v1/books", query_string=query).status_code, 400)
        bad = signer().dumps({"version": 1, "s": "price", "filters": {}, "values": ["oops", 1]})
        self.assertEqual(self.client.get("/api/v1/books", query_string={"sort": "price", "cursor": bad}).status_code, 400)

    def test_invalid_inputs_and_limit_cap(self):
        invalid = ["sort=foo", "sort=--id", "limit=0", "limit=-1", "limit=x", "category=abc",
                   "category=0", "cursor=not-base64", "cursor=", "sort=", "limit=1&limit=2", "unknown=x"]
        if not self.multi:
            invalid += ["sort=-price,title"]
        for query in invalid:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/v1/books?" + query).status_code, 400)
        self.assertEqual(self.page(limit=1000)["page"]["limit"], 100)

    def test_insert_between_pages(self):
        first = self.page(sort="-id", limit=5)
        db.session.add(Book(title="Inserted", isbn="9781111111111", price_vnd=100000,
                            stock=1, category_id=1))
        db.session.commit()
        rest = self.collect(sort="-id", limit=5, cursor=first["page"]["next"])
        ids = [r["id"] for r in first["data"] + rest]
        self.assertEqual(ids, [f"book_{i}" for i in range(30, 0, -1)])

    def test_deleted_boundary_and_exact_last_page(self):
        first = self.page(sort="price", limit=5)
        boundary = int(first["data"][-1]["id"][5:])
        db.session.delete(db.session.get(Book, boundary))
        db.session.commit()
        rest = self.collect(sort="price", limit=5, cursor=first["page"]["next"])
        ids = [r["id"] for r in first["data"] + rest]
        self.assertEqual(len(ids), 30)
        self.assertEqual(len(set(ids)), 30)
        last = self.page(limit=29)
        self.assertFalse(last["page"]["more"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

