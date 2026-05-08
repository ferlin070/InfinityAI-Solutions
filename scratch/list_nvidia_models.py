import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("NVIDIA_NIM_API_KEY")

url = "https://integrate.api.nvidia.com/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "accept": "application/json"
}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    models = response.json()
    for model in models['data']:
        print(model['id'])
else:
    print(f"Error: {response.status_code} - {response.text}")
