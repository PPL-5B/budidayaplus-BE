from locust import HttpUser, TaskSet, task, between
import json
from datetime import datetime

# Authentication API Tasks
class AuthenticationTasks(TaskSet):
    def on_start(self):
        """Executed when a simulated user starts."""
        self.phone_number = "08123456789"
        self.password = "AkuAnakEmo"
        self.first_name = "Omar"
        self.last_name = "Khalif"
        self.access_token = None
        self.refresh_token = None

        # Register a user
        self.register_user()

    def register_user(self):
        """Simulate user registration."""
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
        except Exception as e:
            print(f"Register error: {e}")

    @task
    def login(self):
        """Simulate user login."""
        payload = {
            "phone_number": self.phone_number,
            "password": self.password
        }
        try:
            self.client.post("/api/auth/login", json=payload)
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


# Food Sampling API Tasks
class FoodSamplingTasks(TaskSet):
    def on_start(self):
        """Executed when a simulated user starts."""
        self.cycle_id = "test-cycle-id"
        self.pond_id = "test-pond-id"
        self.sampling_id = "test-sampling-id"
        self.access_token = self.login()

    def login(self):
        """Simulate user login to get an access token."""
        try:
            response = self.client.post(
                "/api/auth/login",
                json={"phone_number": "08123456789", "password": "AkuAnakEmo"}
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("access")
            else:
                print(f"Login failed with status: {response.status_code}")
        except Exception as e:
            print(f"Login error in FoodSamplingTasks: {e}")
        return None

    @task
    def get_food_sampling(self):
        """Simulate fetching a specific food sampling."""
        if self.access_token:
            try:
                self.client.get(
                    f"/api/food-sampling/{self.cycle_id}/{self.pond_id}/{self.sampling_id}/",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
            except Exception as e:
                print(f"Get food sampling error: {e}")

    @task
    def list_food_samplings(self):
        """Simulate listing all food samplings for a pond."""
        if self.access_token:
            try:
                self.client.get(
                    f"/api/food-sampling/{self.pond_id}/",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
            except Exception as e:
                print(f"List food samplings error: {e}")

    @task
    def get_latest_food_sampling(self):
        """Simulate fetching the latest food sampling for a pond and cycle."""
        if self.access_token:
            try:
                self.client.get(
                    f"/api/food-sampling/{self.cycle_id}/{self.pond_id}/latest/",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
            except Exception as e:
                print(f"Get latest food sampling error: {e}")

    @task
    def create_food_sampling(self):
        """Simulate creating a new food sampling."""
        if self.access_token:
            payload = {
                "food_quantity": 30,
                "recorded_at": datetime.now().isoformat()
            }
            try:
                self.client.post(
                    f"/api/food-sampling/{self.cycle_id}/{self.pond_id}/",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
            except Exception as e:
                print(f"Create food sampling error: {e}")


# Locust User Classes
class AuthenticationUser(HttpUser):
    tasks = [AuthenticationTasks]
    wait_time = between(1, 3)
    host = "http://localhost:8000/"  # Base host URL


class FoodSamplingUser(HttpUser):
    tasks = [FoodSamplingTasks]
    wait_time = between(1, 3)
    host = "http://localhost:8000/"  # Base host URL