"""MVP authentication contract tests."""

from app.main import app


def test_registration_is_local_only() -> None:
    """Registration must not expose external verification or require contact data."""
    schema = app.openapi()
    assert not any(path.startswith("/api/v1/verification") for path in schema["paths"])

    user_register = schema["components"]["schemas"]["UserRegister"]
    assert set(user_register["properties"]) == {"username", "password"}
