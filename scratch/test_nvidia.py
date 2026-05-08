import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = NVIDIA_API_KEY
)

try:
    completion = client.chat.completions.create(
      model="meta/llama3-70b-instruct",
      messages=[{"role":"user","content":"Hello"}],
      temperature=0.7,
      max_tokens=10
    )
    print("Success!")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"Error: {str(e)}")
