from app.security import create_access_token, decode_access_token, hash_password, verify_password

def test_password_hashing():
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)

def test_access_token_round_trip():
    token = create_access_token("42", "customer")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "customer"
