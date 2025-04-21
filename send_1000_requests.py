import requests

for i in range(1000):
    res = requests.post(
        "http://localhost:8000/api/fish-death/7116a84e-db29-48fe-889b-18d2257e7f98/3518d063-7014-4616-9032-8abc35f759ea/",
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQ1MjU2MTI4LCJpYXQiOjE3NDUxNjk3MjgsImp0aSI6ImFkN2RmZjZkNjBmZTQ2NDRiMzU1NDJiNDBmNDQxZGI4IiwidXNlcl9pZCI6NX0.4g7CcOTHbwKWM3bBZ-NVOkjhms-1cWbB0zMZAKUP03E",
            "Content-Type": "application/json"
        },
        json={"fish_death_count": 5}
    )
    print(f"[{i+1}] Status: {res.status_code}")
