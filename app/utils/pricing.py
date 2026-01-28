def get_plan(api_key: str):
    if api_key.startswith("pro_"):
        return "pro"
    elif api_key.startswith("ultra_"):
        return "ultra"
    return "free"
