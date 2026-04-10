import re

def camel_to_snake(name: str) -> str:
    """
    将驼峰命名转为下划线命名，例如：
      'myVariableName' → 'my_variable_name'
      'HTMLParser'      → 'html_parser'
      'XML2JSON'        → 'xml2_json'  （可选处理）
    """
    # 在小写字母/数字后 + 大写字母前插入下划线
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # 在小写/大写字母或数字后 + 大写字母前插入下划线
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def convert_dict_keys_to_snake(data: dict) -> dict:
    """递归地将字典中所有 key 从驼峰转为下划线命名"""
    if not isinstance(data, dict):
        return data
    return {
        camel_to_snake(k): convert_dict_keys_to_snake(v) if isinstance(v, dict) else v
        for k, v in data.items()
    }


def generate_key2dict(list_data):

    result = {}
    for dict_data in list_data:

        dict_data = convert_dict_keys_to_snake(dict_data)
        if dict_data["uni_code"] in result:
            raise Exception(f'uni_code({dict_data["uni_code"]})重复出现，需要排查请求数据')
        result[dict_data["uni_code"]] = dict_data

    return result




if __name__ == '__main__':
    original = {
        "uniCode": "asdasd",
        "subSystem": "D-WWA",
        "buildingLevel": "Fab1F2",
        "field": "WM33",
        "idShort": "04",
        "interfaceCode": "D-WWA;Fab1F2;WM33;04",
        "extraData": {
            "deviceType": "TAKEOFF",
            "isValid": True
        }
    }

    # converted = convert_dict_keys_to_snake(original)
    #
    # import json
    # print(json.dumps(converted, indent=4, ensure_ascii=False))

    result = generate_key2dict(original)
    print(result)
