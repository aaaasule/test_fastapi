import requests
import json
import os

API_URL = "http://127.0.0.1:8080/api/fid_checker"
DXF_FILE_PATH = os.path.abspath("YMTC^FID.PS^FAB1^F2.dxf")
DXF_FILE_PATH = os.path.abspath("YMTC^FID.PS^FAB2^F2.dxf")
DXF_FILE_PATH = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.ES^FAB2^F2.dxf")

#FID默认
DXF_FILE_PATH = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.ES^FAB2^F2.dxf")
#DXF_FILE_PATH = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\YMTC^FID.PA^FAB1^F2.dxf")

#DXF_FILE_PATH = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.PS^FAB2^F2.dxf")
#DXF_FILE_PATH = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.PB^FAB2^F2.dxf")



#DXF_FILE_PATH = r"C:\Users\w8856\Desktop\新建文件夹\数据\DXF图纸\DXF图纸\ES\YMTC^FID.ES^FAB1^F1.dxf"
DXF_FILE_PATH = r"./temp_uploads/YMTC^FID.PS^FAB1^F2.dxf"
data = json.load(open(r'C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.ES^FAB2^F2.json', 'r', encoding='utf-8'))

company = data['company']
fab = data['fab']
building = data['building']
buildingLevel = data['buildingLevel']
system = data['system']
subsystemList = data['subsystemList']
fieldList = data['fieldList']
interfaceList = data['interfaceList']
systemInterfaceList = data['systemInterfaceList']


form_data = {'company': company,
        "fab":  fab,
        "building":  building,
        "buildingLevel": buildingLevel,
        "system": system,
        'subsystemList': subsystemList,
        'fieldList': fieldList,
        'interfaceList': interfaceList,
        "systemInterfaceList": systemInterfaceList
        }

form_data = {k:json.dumps(v, ensure_ascii=False) for k,v in form_data.items()}
#print(form_data)

#print(json.dumps(form_data, indent=2, ensure_ascii=False))

# 上传文件
with open(DXF_FILE_PATH, "rb") as f:
    files = {
        "file": (os.path.basename(DXF_FILE_PATH), f, "application/dxf")
    }
    response = requests.post(
        API_URL,
        data=form_data,   # ← 普通字段用 data
        files=files,      # ← 文件用 files
        timeout=3000
    )


# 处理响应
if response.status_code == 200:
    print("✅ 成功:", json.dumps(response.json(), indent=4,  ensure_ascii=False))
else:
    print("❌ 失败:", response.status_code, response.text)


#print(len(response.json()['data']['interfaces']))

field_errors = []
all_errors = []
#data = json.loads(response.json()['data'])
data = response.json()['data']
# for d in data['field']:
#     if d['operation'] == 'delete':
#         print(d['id'], d['operation'])

import json
with open(r'C:\Users\w8856\Desktop\新建文件夹\数据\Output\Output\Field.json', 'r', encoding='utf-8') as f:

    xu_data = json.load(f)


xu_field_unicode = [d['uni_code'] for d in xu_data]

print(len(xu_field_unicode))
print(len(data['field']))
print(f"interface数量{len(data['interfaces'])} field数量{len(data['field'])}")

field_unicode = [d['uniCode'] for d in data['field']]

for xu_field in xu_field_unicode:
    if xu_field not in field_unicode:
        print(xu_field)


raise Exception
#for k in ['field', 'interfaces']:
for k in ['field']:
    # for d in data['field']:
    #     if d['id'] != None and d['operation'] != 'delete':
    #         print(d['id'], d['operation'])
    # print('-'*100)
    # for d in data['field']:
    #     if d['operation'] == 'delete' and d['id'] == None:
    #         print(d['id'], d['operation'])
    # print('-'*100, f"{k} over")

    for d in data[k]:
        if d['uniCode'] not in xu_field_unicode:
            print(d['uniCode'])

