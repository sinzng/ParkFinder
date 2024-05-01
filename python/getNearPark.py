#!/usr/bin/env python

import requests
import pandas as pd
import requests
import googlemaps
from geopy.distance import geodesic
import json
from fastapi import FastAPI, HTTPException
import os
import pydantic
from pymongo import mongo_client
from bson.objectid import ObjectId

pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

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

# MongoDB에 연결
db = client["projectjh"]
collection = db["park"]
# 특정 컬렉션의 데이터를 가져오기
data_from_mongodb = collection.find()
# 가져온 데이터를 리스트로 변환
data_list = list(data_from_mongodb)

# 주소 -> 좌표(위도,경도) 전환 API 활용
mykey = get_secret('google_apiKey')
maps = googlemaps.Client(key=mykey)
def geocode(address):
    geocode_result = maps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        return None
def nearpark(address, limit=5) :

    # 사용자의 좌표 (예: 서울의 위도와 경도)
    user_address = address
    user_coordinates = geocode(user_address)

    # MongoDB 컬렉션에서 데이터 가져오기
    data = collection.find()

    # 가장 가까운 공원 10개 찾기
    park_distances = []  # 공원과 사용자 간의 거리를 저장할 리스트
    for park_info in data:
        park_coordinates = (park_info["lat"], park_info["lng"])  # 공원의 위도와 경도
        distance = geodesic(user_coordinates, park_coordinates).kilometers
        park_distances.append((park_info["name"], distance))  # 공원 이름과 거리를 튜플로 저장

    # 거리를 기준으로 정렬
    park_distances.sort(key=lambda x: x[1])

    nearest_parks = []
    for i, (park, distance) in enumerate(park_distances[:limit], 1):
        nearest_parks.append({"park": park, "distance": distance})

    return nearest_parks

# 함수를 사용하여 가장 가까운 공원 10개 찾기
nearest_parks = nearpark('언주로 98길 35-12')