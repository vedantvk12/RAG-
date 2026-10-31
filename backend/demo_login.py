import requests

# 1. Login to get cookie
resp = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    data={"username": "demo@example.com", "password": "password123"}
)
print("Login status:", resp.status_code)

cookies = resp.cookies

# 2. Get /auth/me
me_resp = requests.get("http://localhost:8000/api/v1/auth/me", cookies=cookies)
print("Me status:", me_resp.status_code)
print("Me JSON:", me_resp.json())
