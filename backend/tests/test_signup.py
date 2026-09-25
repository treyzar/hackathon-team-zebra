"""Signup: a new user is a student with the full name they entered."""

from conftest import requires_db

pytestmark = requires_db

FORM = {
    "email": "ivanov@example.com",
    "username": "ivanov",
    "password": "password123",
    "name": "Иван",
    "surname": "Иванов",
    "patronymic": "Петрович",
}


async def test_signup_stores_full_name(client):
    r = await client.post("/auth/signup", json=FORM)
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    me = (
        await client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
    ).json()
    assert (me["name"], me["surname"], me["patronymic"], me["role"]) == (
        "Иван",
        "Иванов",
        "Петрович",
        "student",
    )


async def test_signup_patronymic_optional_and_duplicates(client):
    no_patronymic = {k: v for k, v in FORM.items() if k != "patronymic"}
    assert (await client.post("/auth/signup", json=no_patronymic)).status_code == 201
    again = await client.post("/auth/signup", json={**FORM, "email": "x@example.com"})
    assert again.status_code == 409
    no_name = {k: v for k, v in FORM.items() if k != "name"}
    no_name["username"] = "petrov"
    assert (await client.post("/auth/signup", json=no_name)).status_code == 422
