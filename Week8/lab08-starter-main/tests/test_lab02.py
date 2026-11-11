"""Check real API responses against the Book contract, beyond static linting."""
from copy import deepcopy

import pytest
from jsonschema import ValidationError, validate

from tools import get_book_schema


@pytest.fixture()
def book_json_schema():
    schema = deepcopy(get_book_schema())
    # OpenAPI 3.0 nullable is not a JSON Schema keyword.
    for field in schema["properties"].values():
        if field.pop("nullable", False):
            field["type"] = [field["type"], "null"]
    return schema


@pytest.mark.parametrize("optional", [{}, {"year": 2021, "isbn": "9781617295850"}])
def test_book_response_matches_contract(client, book_json_schema, optional):
    created = client.post("/books", json={"title": "Book", "author": "Author", **optional})
    assert created.status_code == 201
    validate(instance=created.get_json(), schema=book_json_schema)

    response = client.get(f"/books/{created.get_json()['id']}")
    assert response.status_code == 200
    validate(instance=response.get_json(), schema=book_json_schema)


@pytest.mark.parametrize(
    "change, rejected_keyword",
    [({"password_hash": "simulated-secret"}, "additionalProperties"),
     ({"year": "2021"}, "type")],
)
def test_contract_rejects_invalid_response(client, sample_book, book_json_schema, change, rejected_keyword):
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200
    data = response.get_json()
    validate(instance=data, schema=book_json_schema)

    invalid = deepcopy(data)
    invalid.update(change)
    with pytest.raises(ValidationError) as caught:
        validate(instance=invalid, schema=book_json_schema)
    assert caught.value.validator == rejected_keyword
