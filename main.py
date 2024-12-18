from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import csv
import asyncio
import aiohttp

DEFAULT_CSV_FILE = 'europe.csv'
WEATHER_API_URL = 'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true'

app = FastAPI()
templates = Jinja2Templates(directory='templates')

cities = []

def load_cities():
    global cities
    with open(DEFAULT_CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cities.append({
                'country': row['country'],
                'name': row['capital'],
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'weather': 'N/A'
            })
    return cities

async def fetch_weather(session, city):
    url = WEATHER_API_URL.format(latitude=city['latitude'], longitude=city['longitude'])
    url = f'https://api.open-meteo.com/v1/forecast?latitude={city['latitude']}&longitude={city['longitude']}&current_weather=true'
    try:
        async with session.get(url) as response:
            result = await response.json()
            city['weather'] = result['current_weather']['temperature']
    except Exception as e:
        city['weather'] = 'Error'

# Initialize cities list
load_cities()

# Models for adding/removing cities
class City(BaseModel):
    country: str
    name: str
    latitude: float
    longitude: float

class CityName(BaseModel):
    name: str

@app.get('/', response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/weather/update')
async def update_weather():
    async def fetch_weather(city):
        url = f'https://api.open-meteo.com/v1/forecast?latitude={city['latitude']}&longitude={city['longitude']}&current_weather=true'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return {
                    'name': city['name'],
                    'country': city['country'],
                    'weather': data.get('current_weather', {}).get('temperature', 'N/A')
                }

    tasks = [fetch_weather(city) for city in cities]
    updated_cities = await asyncio.gather(*tasks)
    return updated_cities

@app.post('/cities/add')
async def add_city(city: City):
    if any(c['name'].lower() == city.name.lower() for c in cities):
        raise HTTPException(status_code=400, detail='City already exists.')
    cities.append({'country': city.country, 'name': city.name, 'latitude': city.latitude, 'longitude': city.longitude})
    return {'message': f'City {city.name} added successfully.'}

@app.delete('/cities/remove')
async def remove_city(city: CityName):
    global cities
    cities = [c for c in cities if c['name'].lower() != city.name.lower()]
    return {'message': f'City {city.name} removed successfully.'}

@app.post('/cities/reset')
async def reset_cities():
    load_cities()
    return {'message': 'Cities list reset to default.'}