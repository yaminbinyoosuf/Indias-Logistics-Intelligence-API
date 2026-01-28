def verify_api_key(api_key: str, valid_keys: str) -> bool:
    return api_key in valid_keys.split(",")
