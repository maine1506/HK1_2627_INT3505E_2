import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Bai2.app import create_app
from Lab2 import test_pagination as shared


class AdvancedPaginationTests(shared.CursorTests):
    factory = staticmethod(create_app)
    multi = True

    def test_offset_and_cursor_agree_on_multikey_order(self):
        for sort in ("-price,title", "title,-price", "stock,-price,title", "-title,price,-id"):
            with self.subTest(sort=sort):
                cursor_rows = self.collect(sort=sort, limit=3, genre="tech")
                offset_rows = []
                for offset in range(0, 12, 3):
                    page = self.page(strategy="offset", offset=offset, limit=3, sort=sort, genre="tech")
                    self.assertEqual(page["pagination"]["total"], 10)
                    offset_rows.extend(page["data"])
                self.assertEqual([r["id"] for r in cursor_rows], [r["id"] for r in offset_rows])
                self.assertEqual(len({r["id"] for r in cursor_rows}), 10)
                # Independent Python oracle for mixed sort directions.
                expected = self.page(strategy="offset", sort="id", limit=100, genre="tech")["data"]
                fields = {"price": lambda r: r["price"]["amount"], "title": lambda r: r["title"],
                          "stock": lambda r: r["stock"], "id": lambda r: int(r["id"][5:])}
                tokens = sort.split(",")
                if not any(t.lstrip("-") == "id" for t in tokens):
                    tokens.append("-id" if tokens[-1].startswith("-") else "id")
                for token in reversed(tokens):
                    expected.sort(key=fields[token.lstrip("-")], reverse=token.startswith("-"))
                self.assertEqual([r["id"] for r in cursor_rows], [r["id"] for r in expected])

    def test_strategy_and_genre_errors(self):
        for query in ("strategy=bad", "strategy=offset&cursor=x", "strategy=cursor&offset=0",
                      "strategy=offset&offset=-1", "sort=price,price", "sort=id,title", "genre="):
            self.assertEqual(self.client.get("/api/v1/books?" + query).status_code, 400)
        token = self.page(genre="tech", sort="-price,title", limit=2)["page"]["next"]
        self.assertEqual(self.client.get("/api/v1/books", query_string={
            "genre": "fiction", "sort": "-price,title", "cursor": token}).status_code, 400)
        self.assertEqual(self.page(genre="unknown")["data"], [])
        empty = self.page(strategy="offset", offset=1000)
        self.assertEqual(empty["data"], [])
        self.assertFalse(empty["pagination"]["has_next"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
