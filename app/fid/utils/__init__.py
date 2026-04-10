
import json
def safe_json_loads(val):
    return val if isinstance(val, (list, dict)) else json.loads(val)

def safe_dump_loads(val):
    return val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
