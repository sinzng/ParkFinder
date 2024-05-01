#!/usr/bin/env python
import pandas as pd
import json
import csv
import requests
from pymongo import mongo_client
import os
import matplotlib.pyplot as plt
from gridfs import GridFS
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.relpath("./")))
secret_file = os.path.join(BASE_DIR, '../secret.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        errorMsg = "Set the {} environment variable.".format(setting)
        return errorMsg


HOSTNAME = get_secret("Local_Mongo_Hostname")
USERNAME = get_secret("Local_Mongo_Username")
PASSWORD = get_secret("Local_Mongo_Password")

client = mongo_client.MongoClient(f'mongodb://{USERNAME}:{PASSWORD}@{HOSTNAME}:27017/')
# 데이터베이스와 컬렉션 선택
db = client['projectjh']
collection = db['dogs']

# 지역별 견종 비율
def get_breed_ratio(region):
    breed_ratio_by_region = {}
    cursor = collection.find({"SGG":region}, {"_id":0, "SPCS":1, "CNT":3})
    # 전체 견종 수 및 개체 수 초기화
    total_count = 0
    # 조회된 데이터를 기반으로 견종 비율 계산
    for document in cursor:
        breed = document.get("SPCS")
        count = document.get("CNT")

        # 견종의 카운트 누적
        total_count += count

        # 해당 견종의 카운트 누적
        if breed not in breed_ratio_by_region:
            breed_ratio_by_region[breed] = count
        else:
            breed_ratio_by_region[breed] += count

    # 상위 5개 견종만 선택하여 출력
    top_5_breeds = dict(sorted(breed_ratio_by_region.items(), key=lambda item: item[1], reverse=True)[5:10])

    # 각 견종의 비율 계산
    breed_ratio_result = {}
    for breed, count in top_5_breeds.items():
        breed_ratio = (count / total_count) * 100  # 비율을 백분율로 변환
        breed_ratio_result[breed] = round(breed_ratio, 2)  # 소숫점 두 번째 자리까지 반올림
        breed_ratio_result[breed] = str(breed_ratio_result[breed]) + "%"  # % 문자 추가

    return breed_ratio_result
region = "강남구"
breed_ratio = get_breed_ratio(region)
print(breed_ratio)
print(type(breed_ratio))

plt.rcParams['font.family'] = 'NanumBarunGothic'

def create_pie_chart(region):

    db = client["projectjh"]
    fs = GridFS(db)


    breed_ratio = get_breed_ratio(region)

    breeds = list(breed_ratio.keys())
    # % 기호를 제거하고 실수형으로 변환
    ratios = [float(value.replace('%', '')) for value in breed_ratio.values()]
    colors = ['#c6dbda', '#fee1e8', '#fed7c3', '#f6eac2', '#ecd5e3']

    #파이 차트 생성
    plt.figure(figsize=(8, 10))
    plt.pie(ratios, labels=breeds,colors=colors, autopct='%1.1f%%')
    plt.title(f'{region} 친구들 ')

    # 이미지를 파일로 저장하는 대신에 이미지를 메모리에 저장하고, 바이트 형태로 변환
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=400, bbox_inches='tight')
    img_buffer.seek(0)

    # 이미지를 GridFS에 저장하고 해당 파일의 ObjectId를 반환
    with img_buffer as file:
        file_id = fs.put(file, filename=f'breed_ratio_{region}.png')
    print(file_id)
    # 저장된 이미지 파일의 ObjectId 반환
    return str(file_id)