#!/usr/bin/env python

import requests
import googlemaps
import time
from typing import List
from geopy.distance import geodesic
import json
from fastapi import FastAPI, HTTPException, Response
import os
import pydantic
from pymongo import mongo_client
from bson.objectid import ObjectId
from pydantic import BaseModel
from gridfs import GridFS
from starlette.responses import FileResponse
import base64
import mysql.connector
from getNearPark import nearpark, geocode
from getDogData import  get_breed_ratio, create_pie_chart


pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

app = FastAPI()

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
db = client["projectjh"]



def get_address_from_location(location):
    # 이전에 입력받은 주소가 아닌 경우 구글 Maps API 호출
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': location,
        'key': get_secret('google_apiKey'),  # 자신의 Google Geocoding API 키로 대체
        'region': 'KR'  # 한국 기준으로 주소 검색
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'results' in data and data['results']:
        formatted_address = data['results'][0]['formatted_address']
        return formatted_address
    else:
        return None
    
def get_location_from_addr(addr):
    # 이전에 입력받은 주소가 아닌 경우 구글 Maps API 호출
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': addr,
        'key': get_secret('google_apiKey'),  # 자신의 Google Geocoding API 키로 대체
        'region': 'KR'  # 한국 기준으로 주소 검색
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'results' in data and data['results']:
        latitude = data['results'][0]['geometry']['location']['lat']
        longitude = data['results'][0]['geometry']['location']['lng']
        return latitude, longitude
    else:
        return None
    
# 주소 -> 좌표(위도,경도) 전환 API 활용
api_key = get_secret('google_apiKey')
maps = googlemaps.Client(key=api_key)
def get_parkRanking(location):
    parks_data = []
    next_page_token = None
    addr =maps.geocode(location)
    lat = addr[0]['geometry']['location']['lat']
    lng = addr[0]['geometry']['location']['lng']
    while True:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f'{lat},{lng}',
            'radius': 2000, 
            'key': api_key,
            'keyword': '공원',
            'type':'park',
            'language':'ko',
            'pagetoken': next_page_token  # 첫 요청에서는 None이므로 파라미터가 무시됨
        }

        response = requests.get(url, params=params)
        results = response.json()

        for place in results['results']:
            parks_data.append({
                'name': place.get('name'),
                'address': place.get('vicinity'),
                'lat': place.get('geometry')['location']['lat'],
                'lng': place.get('geometry')['location']['lng']
            })

        next_page_token = results.get('next_page_token')
        if not next_page_token or 'error_message' in results:
            break
        time.sleep(2)  # API 요구사항에 따라 토큰 간 2초 대기

    return parks_data

# Pydantic 모델을 사용하여 응답 데이터 형식 정의
class ParkData(BaseModel):
    name: str
    address: str
    lat: float
    lng: float

def savetomongodb(data,collection_name):
    # MongoDB에 연결
    db = client["projectjh"]
    collection = db[collection_name]
    try:
        # MongoDB에 데이터 삽입
        result = collection.insert_many(data)

        # 삽입된 데이터 조회
        inserted_ids = result.inserted_ids
        inserted_data = list(collection.find({"_id": {"$in": inserted_ids}}, {"_id": 0}).limit(5))

        return {"code":200,"type":collection_name,"data":inserted_data}
    except Exception as e:
        # 그 외의 예외가 발생하면 서버 오류로 간주합니다.
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/parks')
async def get_all_parks(location: str):
    type = "park"
    # 서울시 각 구의 동들을 딕셔너리로 정의, 나중에 데이터 많아지면 파일로 저장하든가 말든가ㅣ...ㅎ ㅎ
    areas_by_location = {
        "강남구": ["신사동", "논현동", "압구정동", "청담동", "삼성동", "대치동", "역삼동",
                "도곡동", "개포동", "세곡동", "일원동", "수서동"],
        "서초구": ['잠원동', '반포동', '서초동','방배동', '양재동', '내곡동','우면동']
    }
    # 입력한 지역에 따라 해당하는 동들의 리스트 가져오기
    areas = areas_by_location.get(location, [])

    all_parks = []

    # 입력한 지역과 함수 내의 지역을 합쳐서 쿼리를 구성하여 공원 정보를 가져옴
    for area in areas:
        query = f'{location}+{area}'
        park_info = get_parkRanking(query)

        # 리스트로 변환하여 추가
        park_list = []
        for park in park_info:
            park_list.append({
                "name": park["name"],
                "address": park["address"],
                "lat": park["lat"],
                "lng": park["lng"]
            })
        all_parks.extend(park_list)

    # 중복 주소 제거
    unique_parks = {}
    for park in all_parks:
        unique_parks[park["address"]] = park

    # MongoDB에 데이터 저장하고 결과 반환
    return savetomongodb(list(unique_parks.values()), type)
    

key = get_secret("apikey_dog")
@app.get("/dogdata")
async def get_dog_data(start:int, end:int, region:str):
    collection_name= "dogs"
    url = f'http://211.237.50.150:7080/openapi/{key}/json/Grid_20210806000000000612_1/{start}/{end}?CTPV=서울특별시&SGG={region}&LVSTCK_KND=개'
    # 해당 URL로 요청을 보내고 응답을 받아옴
    response = requests.get(url)
    data = response.json()
    # "row" 키에 해당하는 값을 추출하여 MongoDB에 저장
    row_data = data.get("Grid_20210806000000000612_1", {}).get("row", [])
    # "row" 키에 해당하는 값을 추출하여 특정 필드만 저장
    # row_data = []
    # for document in data.get("Grid_20210806000000000612_1", {}).get("row", []):
    #     # 특정 필드만 추출하여 새로운 딕셔너리에 저장
    #     filtered_document = {
    #         "CTPV": document.get("CTPV"),
    #         "SGG": document.get("SGG"),
    #         "SPCS": document.get("SPCS"),
    #         "CNT": document.get("CNT")
    #     }
    #     # 새로운 딕셔너리를 리스트에 추가
    #     row_data.append(filtered_document)

    return row_data

@app.get("/getratio")
async def get_ratio(region:str):
    type ="ratio"
    breed_ratio = get_breed_ratio(region)
    breed_list = [{"breed": breed, "ratio": ratio} for breed, ratio in breed_ratio.items()]
    
    
    return savetomongodb(breed_list, type)


@app.get("/createchart")
async def get_chart(region:str):
    
    fs = GridFS(db)
    # 이미지 파일 생성 및 경로 가져오기
    image_id = create_pie_chart(region)

    # GridFS에서 이미지를 가져옴
    image = fs.get(ObjectId(image_id))
    if image:
    # 이미지 파일을 클라이언트에 전송
        return Response(content=image.read(), media_type='image/jpeg')

    else:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    
print(get_chart("용산구"))
    
MYSQL_CONFIG = {
    'host': get_secret("Mysql_Hostname"),
    'user': get_secret("Mysql_Username"),
    'password': get_secret("Mysql_Password"),
    'database': get_secret("Mysql_DBname"),
    'port': int(get_secret("Mysql_Port"))  # 포트 번호는 정수형으로 변환하여 설정
}
# MySQL 연결 함수
def connect_to_mysql():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print("MySQL 연결 성공:", conn)  # 연결 객체 출력
        return conn
    except Exception as e:
        print("MySQL 연결 실패:", e)  # 연결 실패 시 에러 메시지 출력
        return None

@app.get('/nearparks')
async def get_address(location: str):
        # 이전에 입력받았던 주소인지 확인
    region_info = await get_region_from_mysql(location)
    nearby_parks = []  # 근처 공원을 저장할 변수 초기화
    
    if region_info:
        # 이전에 입력받았던 주소인 경우
        formatted_address = region_info['address']
        latitude = region_info['latitude']
        longitude = region_info['longitude']
        # 이미 검색된 주소이므로 해당 region_id로부터 공원 리스트를 가져옴
        nearby_parks = await get_nearparks_by_region(region_info['id'])
    else:
        # 이전에 입력받은 주소가 아닌 경우 구글 Maps API 호출
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': location,
            'key': get_secret('google_apiKey'),  # 자신의 Google Geocoding API 키로 대체
            'region': 'KR'  # 한국 기준으로 주소 검색
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            # 정상적으로 결과가 반환되었을 때
            location = data['results'][0]['geometry']['location']
            formatted_address = data['results'][0]['formatted_address']
            latitude = location['lat']
            longitude = location['lng']
            
            # MySQL에 주소 삽입
            await insert_address_to_mysql(formatted_address, latitude, longitude)
            
            # 근처 공원 찾기
            nearby_parks = await getNearParks(formatted_address)
            
            # MySQL parks 테이블에 근처 공원 리스트 저장
            for park_data in nearby_parks:
                park_name = park_data["park"]
                distance = park_data["distance"]
                await insert_park_to_mysql(park_name, distance, formatted_address)
            
        else:
            # 결과가 없거나 오류가 발생했을 때
            return {'error': 'No results found or error occurred.'}
    
    return {
        'address': formatted_address,
        'latitude': latitude,
        'longitude': longitude,
        'nearby_parks': nearby_parks
    }
async def get_region_from_mysql(location:str):
    try : 
        conn = connect_to_mysql()
        if conn : 
            cursor = conn.cursor() 

            query = "SELECT * FROM region WHERE address = %s"
            cursor.execute(query,(get_address_from_location(location),))
            region_info = cursor.fetchone()
            cursor.close()
            
            if region_info :
                # 이미 주소가 존재하는 경우 cnt 값을 1 증가시킴
                cursor = conn.cursor()
                update_query = "UPDATE region SET cnt = cnt + 1 WHERE address = %s"
                cursor.execute(update_query, (get_address_from_location(location),))
                conn.commit()
                cursor.close()
                
                return{
                    'id': region_info[0],  # 여기서 'id' 키 추가
                    'address':region_info[1], 
                    'latitude':region_info[2], 
                    'longitude':region_info[3] 
                }
            else :
                # 주소가 존재하지 않는 경우 새로 추가
                cursor = conn.cursor()
                insert_query = "INSERT INTO region (address, latitude, longitude) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (location, 0, 0))  # 예시로 latitude와 longitude를 0으로 초기화
                conn.commit()
                cursor.close()
                
                return None 
        else :
            print("MySQL 연결 실패")
            return None
    except Exception as e:
        print("Error retrieving data from MySQL:", e)
        return None
async def get_nearparks_by_region(region_id: int):
    try:
        conn = connect_to_mysql()
        if conn:
            cursor = conn.cursor()
            # 주어진 region_id로부터 공원 리스트를 가져옴
            query = "SELECT park_name, distance FROM parks WHERE region_id = %s"
            cursor.execute(query, (region_id,))
            park_data = cursor.fetchall()
            parks = [{"park": row[0], "distance": row[1]} for row in park_data]
            cursor.close()
            conn.close()
            return parks
        else:
            print("MySQL 연결 실패")
            return []
    except Exception as e:
        print("Error retrieving parks from MySQL:", e)
        return []
    
async def insert_address_to_mysql(address, latitude, longitude):
    try:
        conn = connect_to_mysql()
        if conn:
            cursor = conn.cursor()

            # 쿼리 실행
            query = "INSERT INTO region (address, latitude, longitude) VALUES (%s, %s, %s)"
            values = (address, latitude, longitude)
            cursor.execute(query, values)

            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            print("MySQL 연결 실패로 데이터 삽입 실패")
            return False
    except Exception as e:
        print("Error inserting data into MySQL:", e)
        return False
    
async def getNearParks(location: str):
    nearest_parks = nearpark(location)

    output_data = []
    for i, park_data in enumerate(nearest_parks, 1):
        park_name = park_data["park"]
        distance = park_data["distance"]
        # print(f"{i}. {park_name}: {distance:.2f} km")
        output_data.append({"park": park_name, "distance": round(distance, 2)})
    return output_data

async def insert_park_to_mysql(park_name, distance, address):
    try:
        conn = connect_to_mysql()
        if conn:
            cursor = conn.cursor()

            # 주소에 해당하는 region_id 가져오기
            query = "SELECT id FROM region WHERE address = %s"
            cursor.execute(query, (get_address_from_location(address),))
            region_id = cursor.fetchone()[0]

            # 쿼리 실행
            query = "INSERT INTO parks (park_name, distance, region_id) VALUES (%s, %s, %s)"
            values = (park_name, distance, region_id)
            cursor.execute(query, values)

            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            print("MySQL 연결 실패로 데이터 삽입 실패")
            return False
    except Exception as e:
        print("Error inserting data into MySQL:", e)
        return False 