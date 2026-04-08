def verify_api_key(api_key: str, valid_keys: str) -> bool:
    return api_key in [key.strip() for key in valid_keys.split(",") if key.strip()]
