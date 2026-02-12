import requests
import json

url = "http://localhost:8000/api/v1/auth/register"
data = {
    "username": "doctor1",
    "email": "doctor@test.com",
    "password": "test123456",
    "full_name": "Test Doctor"
}

print("Sending registration request...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")
print()

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        print("SUCCESS!")
        print(json.dumps(response.json(), indent=2))
    else:
        print("ERROR!")
        print("Response Text:")
        print(response.text[:1000])  # First 1000 chars
except Exception as e:
    print(f"Exception: {e}")
