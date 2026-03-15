import random

from locust import HttpUser, between, task


class URLShortenerUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        username = "loadtest_user"
        with self.client.post(
            "/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "LoadTestPassword123!",
            },
            catch_response=True,
        ) as response:
            if response.status_code == 201 or response.status_code == 409:
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")

        response = self.client.post(
            "/auth/login",
            data={
                "username": username,
                "password": "LoadTestPassword123!",
            },
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

        self.created_short_codes = []

    @task(3)
    def create_short_link(self):
        response = self.client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/very/long/url/for/load/testing",
            },
            headers=self.headers,
        )
        if response.status_code == 201:
            code = response.json().get("short_code")
            if code:
                self.created_short_codes.append(code)

    @task(5)
    def redirect_to_link(self):
        if not self.created_short_codes:
            return

        code = random.choice(self.created_short_codes)
        self.client.get(f"/{code}", allow_redirects=False)

    @task(2)
    def get_stats(self):
        if not self.created_short_codes:
            return

        code = random.choice(self.created_short_codes)
        self.client.get(f"/links/{code}/stats")

    @task(1)
    def search_links(self):
        self.client.get(
            "/links/search?original_url=https://example.com/very/long/url/for/load/testing"
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")
