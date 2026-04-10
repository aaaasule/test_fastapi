from typing import List, Dict, Any


def snake_to_camel(snake_str: str) -> str:
    """将 snake_case 转为 camelCase"""
    if not snake_str:
        return snake_str
    components = snake_str.split('_')
    # 处理连续下划线或空字符串的情况，避免 capitalize 报错或逻辑错误
    return components[0] + ''.join(x.capitalize() if x else '' for x in components[1:])


def rename_dict_keys_to_camel_inplace(d: dict):
    """原地将字典 key 转为 camelCase（仅顶层）"""
    if not d:
        return
    # 收集需要重命名的键，避免在遍历过程中修改字典大小
    keys_to_rename = [k for k in list(d.keys()) if '_' in str(k)]
    for old_key in keys_to_rename:
        new_key = snake_to_camel(old_key)
        # 只有当新键名不同时才操作，防止不必要的赋值
        if new_key != old_key:
            d[new_key] = d.pop(old_key)

    return d

def rename_list_dict_keys_to_camel(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    遍历列表，将其中每个字典的 key 原地转为 camelCase。

    Args:
        data: List[Dict[str, Any]] 类型的列表

    Returns:
        返回同一个列表对象（原地修改），方便链式调用或直接使用
    """
    if isinstance(data, dict):
        return rename_dict_keys_to_camel_inplace(data)

    if not isinstance(data, list):
        return data

    for item in data:
        if isinstance(item, dict):
            rename_dict_keys_to_camel_inplace(item)

    return data


# --- 使用示例 ---
if __name__ == "__main__":
    sample_data = [
        {
            "fab_id": "1",
            "building_level": "L1",
            "tool_code": "EQP_001",
            "insert_point_x": 10.5
        },
        {
            "fab_id": "2",
            "system_id": "SYS_A",
            "is_active": True,
            "nested_info": "ignore_me"  # 注意：此函数默认只处理顶层 key
        }
    ]

    print("转换前:")
    print(sample_data)

    result = rename_list_dict_keys_to_camel(sample_data)

    print("\n转换后:")
    # 输出应为: [{'fabId': '1', 'buildingLevel': 'L1', ...}, ...]
    import json

    print(json.dumps(result, indent=2, ensure_ascii=False))
