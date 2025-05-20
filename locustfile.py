from locust import HttpUser, TaskSet, task, between
import random

class AuthenticationTasks(TaskSet):
    def on_start(self):
        """Executed when a simulated user starts."""
        self.phone_number = "08" + str(random.randint(100000000, 999999999))
        self.password = "lelealomani"
        self.first_name = "alomani"
        self.last_name = "lele"
        self.access_token = None
        self.refresh_token = None

        print(f"Trying to register: {self.phone_number}")
        self.register_user()

    def register_user(self):
        payload = {
            "phone_number": self.phone_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "password": self.password
        }
        try:
            response = self.client.post("/api/auth/register", json=payload)
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get("access")
                self.refresh_token = tokens.get("refresh")
                print(f"Register success: {self.phone_number}")
                self.registered = True
            else:
                print(f"Register failed ({response.status_code}): {response.text}")
                self.registered = False
        except Exception as e:
            print(f"Register error: {e}")
            self.registered = False


    @task
    def login(self):
        """Simulate user login."""
        if not getattr(self, 'registered', False):
            print(f"Skipping login because register failed for {self.phone_number}")
            return
    
        payload = {
            "phone_number": self.phone_number,
            "password": self.password
        }
        try:
            response = self.client.post("/api/auth/login", json=payload)
            if response.status_code == 200:
                print(f"Login success: {self.phone_number}")
            else:
                print(f"Login failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"Login error: {e}")

    @task
    def refresh_token_task(self):
        """Simulate refreshing the access token."""
        if self.refresh_token:
            payload = {"refresh": self.refresh_token}
            try:
                self.client.post("/api/auth/refresh", json=payload)
            except Exception as e:
                print(f"Refresh token error: {e}")

    @task
    def validate_token(self):
        """Simulate validating the access token."""
        if self.access_token:
            try:
                self.client.post("/api/auth/validate", headers={"Authorization": f"Bearer {self.access_token}"})
            except Exception as e:
                print(f"Validate token error: {e}")

    @task
    def get_user_info(self):
        """Simulate retrieving user information."""
        if self.access_token:
            try:
                self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {self.access_token}"})
            except Exception as e:
                print(f"Get user info error: {e}")

class AuthenticationUser(HttpUser):
    tasks = [AuthenticationTasks]
    wait_time = between(1, 3)
    host = "http://127.0.0.1:8000"
