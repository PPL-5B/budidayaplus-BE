import os
import json
import uuid
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth.models import User, AnonymousUser
from ninja_jwt.tokens import RefreshToken
from ninja.responses import Response

from forum.models import Forum, ForumVote
from forum.repositories.forum_repository import ForumRepository
from forum.api import create_forum, get_forums_by_user, get_forum_by_id
from forum.schemas import ForumCreateSchema

class ForumAPITestCase(TestCase):
    def _token(self, user: User):
        return str(RefreshToken.for_user(user).access_token)

    def _req(self, method: str, url: str, token=None, body=None):
        hdrs = {"content_type": "application/json"}
        if token:
            hdrs["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        if body is not None:
            hdrs["data"] = json.dumps(body)

        match method:
            case "GET":
                return self.client.get(url, **hdrs)
            case "POST":
                return self.client.post(url, **hdrs)
            case "PUT":
                return self.client.put(url, **hdrs)
            case "DELETE":
                return self.client.delete(url, **hdrs)
        raise ValueError("Bad HTTP verb")

    def setUp(self):
        self.client = Client()
        pwd = os.getenv("TEST_USER_PASSWORD", "defaultpass123")

        self.user = User.objects.create_user("apiuser", password=pwd)
        self.other = User.objects.create_user("apiother", password=pwd)

        self.token = self._token(self.user)
        self.other_token = self._token(self.other)

        self.post = Forum.objects.create(
            user=self.user, title="Origin", description="Isi"
        )
        self.post_id = str(self.post.id)

    def test_manual_unauthorized_branches(self):
        fake_request = SimpleNamespace(user=AnonymousUser())

        # create_forum -> 403
        data = ForumCreateSchema(title="X", description="Y")
        resp: Response = create_forum(fake_request, data)
        self.assertEqual(resp.status_code, 403)

        # get_forums_by_user -> 403
        resp2: Response = get_forums_by_user(fake_request)
        self.assertEqual(resp2.status_code, 403)

    def test_create_and_reply(self):
        ok = self._req(
            "POST",
            "/api/forum/create",
            self.token,
            {"title": "Baru", "description": "Konten"},
        )
        self.assertEqual(ok.status_code, 200)

        # reply sukses
        pid = ok.json()["id"]
        rep = self._req(
            "POST",
            "/api/forum/create_reply",
            self.token,
            {"description": "Balasan", "parent_id": pid},
        )
        self.assertEqual(rep.status_code, 200)
        self.assertEqual(rep.json()["title"], "Reply Baru Forum")

        # reply tanpa parent_id
        self.assertEqual(
            self._req(
                "POST", "/api/forum/create_reply", self.token, {"description": "x"}
            ).status_code,
            400,
        )

        # create main: missing title → 400
        self.assertEqual(
            self._req(
                "POST", "/api/forum/create", self.token, {"description": "no title"}
            ).status_code,
            400,
        )

        # create main: parent_id random (valid UUID) -> 400
        self.assertEqual(
            self._req(
                "POST",
                "/api/forum/create",
                self.token,
                {
                    "title": "Z",
                    "description": "x",
                    "parent_id": str(uuid.uuid4()),
                },
            ).status_code,
            400,
        )

    def test_listing_and_latest_branches(self):
        # get_by_user sukses
        r = self._req("GET", "/api/forum/get_by_user", self.token)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)

        # list
        self.assertEqual(
            self._req("GET", "/api/forum/list", self.token).status_code, 200
        )

        # detail not‑found
        self.assertEqual(
            self._req("GET", f"/api/forum/get_by_id/{uuid.uuid4()}", self.token).status_code,
            404,
        )

        # replies (success & 404)
        ForumRepository.create_forum(
            user=self.user, title=None, description="Balas", parent=self.post
        )
        self.assertEqual(
            self._req("GET", f"/api/forum/get_replies/{self.post_id}", self.token).status_code,
            200,
        )
        self.assertEqual(
            self._req("GET", f"/api/forum/get_replies/{uuid.uuid4()}", self.token).status_code,
            404,
        )

        # latest success
        latest = self._req("GET", "/api/forum/get_latest", self.token)
        self.assertEqual(latest.status_code, 200)

        # latest 404
        Forum.objects.all().delete()
        self.assertEqual(
            self._req("GET", "/api/forum/get_latest", self.token).status_code, 404
        )

    def test_update_paths(self):
        # success
        up = self._req(
            "PUT", f"/api/forum/{self.post_id}", self.token, {"description": "ubah"}
        )
        self.assertEqual(up.status_code, 200)

        # invalid payload -> 422
        self.assertEqual(
            self._req(
                "PUT",
                f"/api/forum/{self.post_id}",
                self.token,
                {"description": ""},
            ).status_code,
            422,
        )

        # not owner
        self.assertEqual(
            self._req(
                "PUT",
                f"/api/forum/{self.post_id}",
                self.other_token,
                {"description": "x"},
            ).status_code,
            403,
        )

        # not found
        self.assertEqual(
            self._req(
                "PUT",
                f"/api/forum/{uuid.uuid4()}",
                self.token,
                {"description": "y"},
            ).status_code,
            404,
        )

    def test_delete_paths(self):
        # forbidden
        self.assertEqual(
            self._req("DELETE", f"/api/forum/delete/{self.post_id}", self.other_token).status_code,
            403,
        )
        # unauthenticated
        self.assertEqual(
            self._req("DELETE", f"/api/forum/delete/{self.post_id}").status_code,
            401,
        )
        # not found
        self.assertEqual(
            self._req("DELETE", f"/api/forum/delete/{uuid.uuid4()}", self.token).status_code,
            404,
        )
        # success
        f = ForumRepository.create_forum(
            user=self.user, title="Del", description="x"
        )
        self.assertEqual(
            self._req("DELETE", f"/api/forum/delete/{f.id}", self.token).status_code,
            200,
        )

    def test_vote_cycle_and_summary(self):
        self._req("POST", f"/api/forum/upvote/{self.post_id}", self.token, {})
        self._req("POST", f"/api/forum/downvote/{self.post_id}", self.token, {})
        self._req("DELETE", f"/api/forum/cancel_vote/{self.post_id}", self.token)
        s_empty = self._req("GET", f"/api/forum/vote_summary/{self.post_id}", self.token)
        self.assertEqual(s_empty.json()["upvotes"], 0)
        self._req("POST", f"/api/forum/upvote/{self.post_id}", self.token, {})
        self._req("POST", f"/api/forum/downvote/{self.post_id}", self.other_token, {})
        summary = self._req("GET", f"/api/forum/vote_summary/{self.post_id}", self.token)
        self.assertEqual(summary.json()["upvotes"], 1)
        self.assertEqual(summary.json()["downvotes"], 1)
        self.assertEqual(summary.json()["user_vote"], "up")

    def test_reply_paths(self):
        parent_id = self.post_id
        ok = self._req(
            "POST",
            "/api/forum/create_reply",
            self.token,
            {"description": "Balasan", "parent_id": parent_id},
        )
        self.assertEqual(ok.status_code, 200)

        no_pid = self._req(
            "POST", "/api/forum/create_reply", self.token, {"description": "X"}
        )
        self.assertEqual(no_pid.status_code, 400)

        random_uuid = str(uuid.uuid4())
        not_exist = self._req(
            "POST",
            "/api/forum/create_reply",
            self.token,
            {"description": "X", "parent_id": random_uuid},
        )
        self.assertEqual(not_exist.status_code, 400)

    def test_get_by_id_direct_success(self):
        """Memanggil handler langsung dengan user ter‑autentikasi."""
        fake_request = SimpleNamespace(user=self.user)
        result = get_forum_by_id(fake_request, uuid.UUID(self.post_id))
        self.assertEqual(result.id, uuid.UUID(self.post_id))
        
    def test_get_user_votes_success(self):
         """Test retrieving votes for the logged-in user."""
         ForumVote.objects.create(user=self.user, forum=self.forum, vote_choice="up")
         response = self._authenticated_get("/api/forum/user_votes", self.user_token)
         self.assertEqual(response.status_code, 200)
         self.assertEqual(len(response.json()["votes"]), 1)
         self.assertEqual(response.json()["votes"][0]["vote_choice"], "up")
 
    def test_get_user_votes_unauthenticated(self):
         """Test retrieving votes without authentication."""
         response = self.client.get("/api/forum/user_votes")
         self.assertEqual(response.status_code, 401)

    def test_search_forum_success_and_empty(self):
        ForumRepository.create_forum(
            user=self.user,
            title="Diskusi Django",
            description="Pembahasan tentang framework Django"
        )
        ForumRepository.create_forum(
            user=self.user,
            title="Belajar Machine Learning",
            description="Topik pembelajaran ML dari dasar"
        )

        response = self._req("GET", "/api/forum/search?q=django", self.token)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(any("django" in f["title"].lower() for f in result))

        response_not_found = self._req("GET", "/api/forum/search?q=tidakada", self.token)
        self.assertEqual(response_not_found.status_code, 200)
        self.assertEqual(len(response_not_found.json()), 0)

        response_no_query = self._req("GET", "/api/forum/search", self.token)
        self.assertEqual(response_no_query.status_code, 400)