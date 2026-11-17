"""Lab 4: weighted tasks and 1% simulated client failures on year searches.

Run: locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
         -u 10 -r 2 -t 30s --html reports/A.html
"""
import itertools
import os
import random

from locust import HttpUser, between, task

_counter = itertools.count(1)
SIMULATED_FAILURE_RATE = float(os.environ.get("LOCUST_SIMULATED_FAILURE_RATE", "0.01"))
if not 0 <= SIMULATED_FAILURE_RATE <= 1:
    raise ValueError("LOCUST_SIMULATED_FAILURE_RATE must be between 0 and 1")


class BooksUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_books(self):
        self.client.get("/books", name="GET /books")

    @task(2)
    def read_book(self):
        book_id = random.randint(1, 50)
        with self.client.get(
            f"/books/{book_id}", name="GET /books/{id}", catch_response=True
        ) as response:
            # Expected 404 (random id absent) is not an operational failure.
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def create_book(self):
        unique = next(_counter)
        self.client.post(
            "/books",
            json={"title": f"Load test {unique}", "author": "locust",
                  "year": random.choice((1996, 2017, 2021))},
            name="POST /books",
        )

    @task(1)
    def search_by_year(self, year=None):
        if year is None:
            year = random.choice((1996, 2017, 2021))
        with self.client.get(
            "/books", params={"year": year}, name="GET /books?year",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected HTTP status {response.status_code}")
                return
            try:
                books = response.json()
            except ValueError:
                response.failure("Search response is not JSON")
                return
            if not isinstance(books, list) or any(
                not isinstance(book, dict) or book.get("year") != year for book in books
            ):
                response.failure("Search result does not match requested year")
            elif random.random() < SIMULATED_FAILURE_RATE:
                # Artificial client-side failure; the real HTTP response remains 200.
                response.failure("SIMULATED_500: client-side injection (actual HTTP 200)")
