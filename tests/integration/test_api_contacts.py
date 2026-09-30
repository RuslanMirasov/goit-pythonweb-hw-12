"""Інтеграційні тести маршрутів контактів."""

from datetime import date, timedelta

import pytest

from tests.integration.conftest import auth_headers

soon = date.today() + timedelta(days=2)
far = date.today() + timedelta(days=100)

contact_data = {
    "first_name": "Olena",
    "last_name": "Shevchenko",
    "email": "olena@example.com",
    "phone": "+38 (050) 111-22-33",
    "birthday": soon.replace(year=2000).isoformat(),
    "additional_data": "Colleague",
}
second_contact_data = {
    "first_name": "Taras",
    "last_name": "Shevchuk",
    "email": "taras@test.com",
    "phone": "+380677654321",
    "birthday": far.replace(year=2000).isoformat(),
}


@pytest.fixture(scope="module")
def created_contact(client, admin_token):
    response = client.post(
        "/api/contacts/", json=contact_data, headers=auth_headers(admin_token)
    )
    assert response.status_code == 201, response.text
    second = client.post(
        "/api/contacts/", json=second_contact_data, headers=auth_headers(admin_token)
    )
    assert second.status_code == 201, second.text
    return response.json()


def test_contacts_unauthorized(client):
    response = client.get("/api/contacts/")

    assert response.status_code == 401


def test_create_contact(created_contact):
    assert created_contact["first_name"] == "Olena"
    assert created_contact["email"] == "olena@example.com"
    assert "id" in created_contact


def test_create_contact_duplicate_email(client, admin_token, created_contact):
    response = client.post(
        "/api/contacts/", json=contact_data, headers=auth_headers(admin_token)
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Contact with this email already exists"


def test_create_contact_invalid_data(client, admin_token):
    response = client.post(
        "/api/contacts/",
        json={**contact_data, "email": "bad", "birthday": "2999-01-01"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_get_contacts(client, admin_token, created_contact):
    response = client.get("/api/contacts/", headers=auth_headers(admin_token))

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.parametrize(
    "params, expected_names",
    [
        ({"first_name": "ole"}, ["Olena"]),
        ({"last_name": "shev"}, ["Olena", "Taras"]),
        ({"email": "test.com"}, ["Taras"]),
        ({"last_name": "shev", "email": "example"}, ["Olena"]),
        ({"first_name": "Ivan"}, []),
    ],
)
def test_search_contacts(client, admin_token, created_contact, params, expected_names):
    response = client.get(
        "/api/contacts/", params=params, headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert sorted(c["first_name"] for c in response.json()) == expected_names


def test_upcoming_birthdays(client, admin_token, created_contact):
    response = client.get("/api/contacts/birthdays", headers=auth_headers(admin_token))

    assert response.status_code == 200
    assert [c["first_name"] for c in response.json()] == ["Olena"]


def test_upcoming_birthdays_custom_days(client, admin_token, created_contact):
    response = client.get(
        "/api/contacts/birthdays", params={"days": 120}, headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert [c["first_name"] for c in response.json()] == ["Olena", "Taras"]


def test_get_contact(client, admin_token, created_contact):
    response = client.get(
        f"/api/contacts/{created_contact['id']}", headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["email"] == contact_data["email"]


def test_get_contact_not_found(client, admin_token):
    response = client.get("/api/contacts/999", headers=auth_headers(admin_token))

    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"


def test_other_user_cannot_see_contact(client, user_token, created_contact):
    list_response = client.get("/api/contacts/", headers=auth_headers(user_token))
    get_response = client.get(
        f"/api/contacts/{created_contact['id']}", headers=auth_headers(user_token)
    )

    assert list_response.json() == []
    assert get_response.status_code == 404


def test_other_user_can_use_same_email(client, user_token, created_contact):
    response = client.post(
        "/api/contacts/", json=contact_data, headers=auth_headers(user_token)
    )

    assert response.status_code == 201


def test_update_contact(client, admin_token, created_contact):
    updated = {**contact_data, "phone": "+380000000000"}

    response = client.put(
        f"/api/contacts/{created_contact['id']}",
        json=updated,
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "+380000000000"


def test_update_contact_email_conflict(client, admin_token, created_contact):
    response = client.put(
        f"/api/contacts/{created_contact['id']}",
        json={**contact_data, "email": second_contact_data["email"]},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 409


def test_update_contact_not_found(client, admin_token):
    response = client.put(
        "/api/contacts/999",
        json={**contact_data, "email": "new@example.com"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 404


def test_delete_contact(client, admin_token, created_contact):
    url = f"/api/contacts/{created_contact['id']}"

    response = client.delete(url, headers=auth_headers(admin_token))
    repeat = client.delete(url, headers=auth_headers(admin_token))

    assert response.status_code == 200
    assert response.json()["id"] == created_contact["id"]
    assert repeat.status_code == 404
