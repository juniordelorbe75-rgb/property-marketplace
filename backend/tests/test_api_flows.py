import asyncio
import base64
from io import BytesIO
import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from unittest.mock import Mock, patch


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")


from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from PIL import Image

from backend.db import get_db
from backend.auth.login_throttle import reset_login_throttle
from backend.auth.social import create_login_code
from backend.db_models.base import Base
from backend.db_models.property import PropertyDB
from backend.db_models.report import ListingReportDB
from backend.main import app


def valid_png_bytes():
    output = BytesIO()
    Image.new("RGB", (2, 2), color="blue").save(output, format="PNG")
    return output.getvalue()


async def request(
    method,
    path,
    json_body=None,
    token=None,
    include_headers=False,
    idempotency_key=None,
    property_version=None,
    report_version=None,
    safety_version=None,
):
    parsed_url = urlsplit(path)
    if (
        method in {"POST", "PUT"}
        and parsed_url.path.startswith("/properties/")
        and isinstance(json_body, dict)
        and "image_url" not in json_body
        and "image_urls" not in json_body
    ):
        json_body = {
            **json_body,
            "image_url": "https://images.example.com/test-property.jpg",
        }
    if (
        method == "PUT"
        and parsed_url.path.startswith("/properties/")
        and isinstance(json_body, dict)
        and "currency" not in json_body
    ):
        json_body = {**json_body, "currency": "USD"}
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = [(b"content-type", b"application/json")]

    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    if idempotency_key:
        headers.append((b"idempotency-key", idempotency_key.encode()))
    if property_version is not None:
        headers.append((b"x-property-version", str(property_version).encode()))
    if report_version is not None:
        headers.append((b"x-report-version", str(report_version).encode()))
    if safety_version is not None:
        headers.append((b"x-listing-safety-version", str(safety_version).encode()))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed_url.path,
        "raw_path": parsed_url.path.encode(),
        "query_string": parsed_url.query.encode(),
        "root_path": "",
        "headers": headers,
        "client": ("test-client", 50000),
        "server": ("test-server", 80),
    }
    sent_messages = []
    request_received = False

    async def receive():
        nonlocal request_received

        if not request_received:
            request_received = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    try:
        await app(scope, receive, send)
    except Exception:
        # Starlette deliberately re-raises handled server exceptions so test
        # clients can inspect them. A real ASGI server still sends the response.
        if not any(
            message["type"] == "http.response.start"
            for message in sent_messages
        ):
            raise

    start = next(
        message
        for message in sent_messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )

    body_data = json.loads(response_body or b"null")
    if include_headers:
        response_headers = {
            key.decode().lower(): value.decode()
            for key, value in start.get("headers", [])
        }
        return start["status"], body_data, response_headers
    return start["status"], body_data


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        reset_login_throttle()
        self.upload_directory = tempfile.TemporaryDirectory()
        self.upload_directory_patch = patch(
            "backend.routes.uploads.UPLOAD_DIRECTORY",
            new=Path(self.upload_directory.name),
        )
        self.upload_directory_patch.start()
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        def override_get_db():
            yield self.session

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        reset_login_throttle()
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        self.upload_directory_patch.stop()
        self.upload_directory.cleanup()

    def call(
        self,
        method,
        path,
        json_body=None,
        token=None,
        idempotency_key=None,
        property_version=None,
        report_version=None,
        safety_version=None,
    ):
        return asyncio.run(
            request(
                method,
                path,
                json_body,
                token,
                idempotency_key=idempotency_key,
                property_version=property_version,
                report_version=report_version,
                safety_version=safety_version,
            )
        )

    def call_with_headers(self, method, path, json_body=None, token=None):
        return asyncio.run(
            request(method, path, json_body, token, include_headers=True)
        )

    def register_and_login(self, name, email):
        register_status, user = self.call(
            "POST",
            "/users/",
            {
                "name": name,
                "email": email,
                "password": "secure-password",
            },
        )
        login_status, login = self.call(
            "POST",
            "/users/login",
            {
                "email": email,
                "password": "secure-password",
            },
        )

        self.assertEqual(register_status, 200)
        self.assertEqual(login_status, 200)

        return user, login["access_token"]

    def test_registration_login_and_property_creation_over_http(self):
        register_status, user = self.call(
            "POST",
            "/users/",
            {
                "name": "API Seller",
                "email": "api-seller@example.com",
                "password": "secure-password",
            },
        )
        login_status, login = self.call(
            "POST",
            "/users/login",
            {
                "email": "api-seller@example.com",
                "password": "secure-password",
            },
        )
        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "HTTP Test Home",
                "price": 320000,
                "location": "Tampa, Florida",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            login["access_token"],
        )
        listings_status, listings = self.call(
            "GET",
            "/properties/my",
            token=login["access_token"],
        )

        self.assertEqual(register_status, 200)
        self.assertNotIn("password", user)
        self.assertEqual(login_status, 200)
        self.assertEqual(create_status, 200)
        self.assertEqual(property_item["owner_id"], user["id"])
        self.assertEqual(listings_status, 200)
        self.assertEqual([item["id"] for item in listings], [property_item["id"]])

    def test_protected_endpoint_rejects_missing_token(self):
        status, body = self.call("GET", "/users/me")

        self.assertEqual(status, 401)
        self.assertIn("detail", body)

    def test_account_deletion_requires_current_password(self):
        user, token = self.register_and_login(
            "Deletion Safety User",
            "deletion-safety@example.com",
        )

        wrong_status, wrong_body = self.call(
            "DELETE",
            "/users/me",
            {"current_password": "wrong-password"},
            token,
        )
        account_status, account = self.call("GET", "/users/me", token=token)
        delete_status, delete_body = self.call(
            "DELETE",
            "/users/me",
            {"current_password": "secure-password"},
            token,
        )
        expired_status, _expired = self.call("GET", "/users/me", token=token)

        self.assertEqual(wrong_status, 400)
        self.assertEqual(wrong_body["detail"], "Current password is incorrect")
        self.assertEqual(account_status, 200)
        self.assertEqual(account["id"], user["id"])
        self.assertEqual(delete_status, 200)
        self.assertEqual(delete_body["message"], "Account deleted successfully")
        self.assertEqual(expired_status, 401)

    def test_repeated_failed_logins_are_temporarily_throttled(self):
        self.call(
            "POST",
            "/users/",
            {
                "name": "Throttle Test User",
                "email": "throttle@example.com",
                "password": "secure-password",
            },
        )

        for _attempt in range(5):
            status, body = self.call(
                "POST",
                "/users/login",
                {
                    "email": " THROTTLE@example.com ",
                    "password": "incorrect-password",
                },
            )
            self.assertEqual(status, 401)
            self.assertEqual(body["detail"], "Invalid email or password")

        blocked_status, blocked_body, blocked_headers = self.call_with_headers(
            "POST",
            "/users/login",
            {
                "email": "throttle@example.com",
                "password": "secure-password",
            },
        )

        self.assertEqual(blocked_status, 429)
        self.assertEqual(
            blocked_body["detail"],
            "Too many login attempts. Please try again later.",
        )
        self.assertGreater(int(blocked_headers["retry-after"]), 0)
        self.assertEqual(blocked_headers["cache-control"], "no-store")

    def test_successful_login_clears_previous_failures(self):
        self.call(
            "POST",
            "/users/",
            {
                "name": "Recovered Login User",
                "email": "recovered-login@example.com",
                "password": "secure-password",
            },
        )
        for _attempt in range(4):
            failed_status, _failed = self.call(
                "POST",
                "/users/login",
                {
                    "email": "recovered-login@example.com",
                    "password": "incorrect-password",
                },
            )
            self.assertEqual(failed_status, 401)

        success_status, _success = self.call(
            "POST",
            "/users/login",
            {
                "email": "recovered-login@example.com",
                "password": "secure-password",
            },
        )
        after_success_status, _after_success = self.call(
            "POST",
            "/users/login",
            {
                "email": "recovered-login@example.com",
                "password": "incorrect-password",
            },
        )

        self.assertEqual(success_status, 200)
        self.assertEqual(after_success_status, 401)

    def test_readiness_reports_database_success_and_failure(self):
        ready_status, ready = self.call("GET", "/ready")

        failing_session = Mock()
        failing_session.execute.side_effect = OperationalError(
            "SELECT 1",
            {},
            Exception("database offline"),
        )

        def override_failing_db():
            yield failing_session

        app.dependency_overrides[get_db] = override_failing_db
        unavailable_status, unavailable = self.call("GET", "/ready")

        self.assertEqual(ready_status, 200)
        self.assertEqual(ready, {"status": "ready", "database": "ok"})
        self.assertEqual(unavailable_status, 503)
        self.assertEqual(unavailable["detail"], "Database is unavailable")

    def test_every_response_includes_a_unique_request_id(self):
        first_status, _first_body, first_headers = self.call_with_headers(
            "GET",
            "/health",
        )
        second_status, _second_body, second_headers = self.call_with_headers(
            "GET",
            "/health",
        )
        first_id = first_headers.get("x-request-id", "")
        second_id = second_headers.get("x-request-id", "")

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertRegex(first_id, r"^[0-9a-f]{32}$")
        self.assertRegex(second_id, r"^[0-9a-f]{32}$")
        self.assertNotEqual(first_id, second_id)

    def test_private_responses_are_not_cached_but_public_success_can_be(self):
        user, token = self.register_and_login(
            "Private Response User",
            "private-response@example.com",
        )

        login_status, _login, login_headers = self.call_with_headers(
            "POST",
            "/users/login",
            {
                "email": "private-response@example.com",
                "password": "secure-password",
            },
        )
        profile_status, _profile, profile_headers = self.call_with_headers(
            "GET",
            "/users/me",
            token=token,
        )
        public_status, _properties, public_headers = self.call_with_headers(
            "GET",
            "/properties/",
        )
        exchange_status, exchange, exchange_headers = self.call_with_headers(
            "POST",
            "/auth/exchange",
            {"code": create_login_code(user["id"])},
        )

        self.assertEqual(login_status, 200)
        self.assertEqual(profile_status, 200)
        self.assertEqual(public_status, 200)
        self.assertEqual(exchange_status, 200)
        self.assertIn("access_token", exchange)
        for headers in (login_headers, profile_headers, public_headers, exchange_headers):
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            self.assertEqual(headers["x-frame-options"], "DENY")
            self.assertEqual(headers["referrer-policy"], "no-referrer")
            self.assertEqual(headers["content-security-policy"], "frame-ancestors 'none'")
            self.assertEqual(
                headers["permissions-policy"],
                "camera=(), microphone=(), geolocation=(), payment=()",
            )
            self.assertEqual(headers["x-permitted-cross-domain-policies"], "none")
        for headers in (login_headers, profile_headers, exchange_headers):
            self.assertEqual(headers["cache-control"], "no-store")
            self.assertEqual(headers["pragma"], "no-cache")
        self.assertNotIn("cache-control", public_headers)
        self.assertNotIn("pragma", public_headers)

    def test_database_write_failure_returns_safe_retryable_response(self):
        _seller, seller_token = self.register_and_login(
            "Database Failure Seller",
            "database-failure@example.com",
        )
        database_error = OperationalError(
            "INSERT secret table details",
            {"password": "must-not-leak"},
            Exception("private database host details"),
        )

        with patch(
            "backend.repositories.property_repository.commit_or_rollback",
            side_effect=database_error,
        ):
            status, body, response_headers = self.call_with_headers(
                "POST",
                "/properties/",
                {
                    "title": "Unavailable Database Home",
                    "price": 300000,
                    "location": "Phoenix, Arizona",
                    "property_type": "House",
                    "bedrooms": 3,
                    "status": "available",
                },
                seller_token,
            )

        serialized_body = json.dumps(body)
        self.assertEqual(status, 503)
        self.assertEqual(
            body["detail"],
            "Database operation failed. Please try again.",
        )
        self.assertNotIn("must-not-leak", serialized_body)
        self.assertNotIn("private database host", serialized_body)
        self.assertEqual(body["request_id"], response_headers["x-request-id"])
        self.assertEqual(response_headers["cache-control"], "no-store")

    def test_unexpected_failure_returns_safe_traceable_response(self):
        private_error = RuntimeError(
            "internal path C:/private and secret configuration value"
        )

        with patch(
            "backend.routes.properties.get_all_properties",
            side_effect=private_error,
        ):
            status, body, response_headers = self.call_with_headers(
                "GET",
                "/properties/",
            )

        serialized_body = json.dumps(body)
        self.assertEqual(status, 500)
        self.assertEqual(
            body["detail"],
            "An unexpected error occurred. Please try again.",
        )
        self.assertNotIn("C:/private", serialized_body)
        self.assertNotIn("secret configuration", serialized_body)
        self.assertEqual(body["request_id"], response_headers["x-request-id"])
        self.assertEqual(response_headers["cache-control"], "no-store")

    def test_buyer_can_also_create_property_over_http(self):
        buyer, buyer_token = self.register_and_login(
            "Buyer And Seller",
            "buyer-and-seller@example.com",
        )

        status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Buyer Listing",
                "price": 200000,
                "location": "Miami, Florida",
                "property_type": "Condo",
                "bedrooms": 2,
                "status": "available",
            },
            buyer_token,
        )

        self.assertEqual(status, 200)
        self.assertEqual(property_item["owner_id"], buyer["id"])

    def test_property_endpoints_support_bounded_pagination_with_totals(self):
        _seller, seller_token = self.register_and_login(
            "Pagination Seller",
            "pagination-seller@example.com",
        )
        for index in range(12):
            create_status, _property = self.call(
                "POST",
                "/properties/",
                {
                    "title": f"Paginated Home {index}",
                    "price": 100000 + index,
                    "location": "Austin, Texas" if index < 7 else "Denver, Colorado",
                    "property_type": "House",
                    "bedrooms": 2,
                    "status": "available",
                },
                seller_token,
            )
            self.assertEqual(create_status, 200)

        status, page, headers = self.call_with_headers(
            "GET",
            "/properties/?limit=5&offset=5",
        )
        search_status, search_page, search_headers = self.call_with_headers(
            "GET",
            "/properties/search?location=Austin&limit=3&offset=3",
        )

        self.assertEqual(status, 200)
        self.assertEqual(len(page), 5)
        self.assertEqual(headers["x-total-count"], "12")
        self.assertEqual(search_status, 200)
        self.assertEqual(len(search_page), 3)
        self.assertEqual(search_headers["x-total-count"], "7")

    def test_property_creation_is_idempotent_per_seller(self):
        _seller, seller_token = self.register_and_login(
            "Retry Seller",
            "retry-seller@example.com",
        )
        _other_seller, other_token = self.register_and_login(
            "Other Retry Seller",
            "other-retry-seller@example.com",
        )
        creation_key = str(uuid4())
        payload = {
            "title": "Retry Safe Home",
            "price": 425000,
            "location": "Portland, Oregon",
            "property_type": "House",
            "bedrooms": 3,
            "status": "available",
        }

        first_status, first = self.call(
            "POST", "/properties/", payload, seller_token, creation_key
        )
        retry_status, retry = self.call(
            "POST", "/properties/", {**payload, "title": "Changed Retry"},
            seller_token, creation_key
        )
        other_status, other = self.call(
            "POST", "/properties/", payload, other_token, creation_key
        )
        list_status, listings = self.call("GET", "/properties/")

        self.assertEqual(first_status, 200)
        self.assertEqual(retry_status, 200)
        self.assertEqual(retry["id"], first["id"])
        self.assertEqual(retry["title"], "Retry Safe Home")
        self.assertEqual(other_status, 200)
        self.assertNotEqual(other["id"], first["id"])
        self.assertEqual(list_status, 200)
        self.assertEqual(len(listings), 2)

    def test_stale_property_update_cannot_overwrite_newer_seller_edit(self):
        _seller, seller_token = self.register_and_login(
            "Versioned Seller",
            "versioned-seller@example.com",
        )
        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Original Versioned Home",
                "description": "Original description",
                "price": 500000,
                "location": "Seattle, Washington",
                "property_type": "House",
                "bedrooms": 4,
                "bathrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        original_version = property_item["version"]
        update_payload = {
            "title": "Newer Tab Edit",
            "description": property_item["description"],
            "image_url": property_item["image_url"],
            "image_urls": property_item["image_urls"],
            "price": property_item["price"],
            "listing_type": property_item["listing_type"],
            "amenities": property_item["amenities"],
            "location": property_item["location"],
            "property_type": property_item["property_type"],
            "bedrooms": property_item["bedrooms"],
            "bathrooms": property_item["bathrooms"],
            "square_feet": property_item["square_feet"],
            "status": property_item["status"],
        }

        newer_status, newer = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            update_payload,
            seller_token,
            property_version=original_version,
        )
        stale_status, stale = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {**update_payload, "title": "Stale Tab Edit"},
            seller_token,
            property_version=original_version,
        )
        detail_status, detail = self.call(
            "GET", f"/properties/{property_item['id']}"
        )

        self.assertEqual(create_status, 200)
        self.assertEqual(original_version, 1)
        self.assertEqual(newer_status, 200)
        self.assertEqual(newer["version"], 2)
        self.assertEqual(stale_status, 409)
        self.assertIn("changed", stale["detail"])
        self.assertEqual(detail_status, 200)
        self.assertEqual(detail["title"], "Newer Tab Edit")
        self.assertEqual(detail["version"], 2)

        stale_delete_status, stale_delete = self.call(
            "DELETE",
            f"/properties/{property_item['id']}",
            token=seller_token,
            property_version=original_version,
        )
        still_present_status, still_present = self.call(
            "GET", f"/properties/{property_item['id']}"
        )
        self.assertEqual(stale_delete_status, 409)
        self.assertIn("changed", stale_delete["detail"])
        self.assertEqual(still_present_status, 200)
        self.assertEqual(still_present["version"], 2)

    def test_inquiry_creation_is_retry_safe_but_new_duplicates_are_blocked(self):
        _seller, seller_token = self.register_and_login(
            "Inquiry Retry Seller",
            "inquiry-retry-seller@example.com",
        )
        _buyer, buyer_token = self.register_and_login(
            "Inquiry Retry Buyer",
            "inquiry-retry-buyer@example.com",
        )
        _other_buyer, other_buyer_token = self.register_and_login(
            "Other Inquiry Buyer",
            "other-inquiry-buyer@example.com",
        )
        _create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Inquiry Retry Home",
                "price": 350000,
                "location": "Boise, Idaho",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        inquiry_key = str(uuid4())

        first_status, first = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Is this still available?"},
            buyer_token,
            inquiry_key,
        )
        retry_status, retry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "A changed retry message"},
            buyer_token,
            inquiry_key,
        )
        duplicate_status, duplicate = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "This is a genuinely new attempt"},
            buyer_token,
            str(uuid4()),
        )
        other_status, other = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "A separate buyer can inquire"},
            other_buyer_token,
            inquiry_key,
        )
        sent_status, sent = self.call(
            "GET", "/inquiries/sent", token=buyer_token
        )

        self.assertEqual(first_status, 200)
        self.assertEqual(retry_status, 200)
        self.assertEqual(retry["id"], first["id"])
        self.assertEqual(retry["message"], "Is this still available?")
        self.assertEqual(duplicate_status, 409)
        self.assertIn("pending inquiry", duplicate["detail"])
        self.assertEqual(other_status, 200)
        self.assertNotEqual(other["id"], first["id"])
        self.assertEqual(sent_status, 200)
        self.assertEqual(len(sent), 1)

    def test_seller_dashboard_stats_are_ownership_isolated(self):
        _seller, seller_token = self.register_and_login(
            "Dashboard Seller",
            "dashboard-seller@example.com",
        )
        _buyer, buyer_token = self.register_and_login(
            "Dashboard Buyer",
            "dashboard-buyer@example.com",
        )
        _status, available = self.call(
            "POST",
            "/properties/",
            {
                "title": "Available Dashboard Home",
                "price": 320000,
                "location": "Dallas, Texas",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        self.call(
            "POST",
            "/properties/",
            {
                "title": "Unavailable Dashboard Home",
                "price": 280000,
                "location": "Dallas, Texas",
                "property_type": "House",
                "bedrooms": 2,
                "status": "unavailable",
            },
            seller_token,
        )
        self.call("POST", f"/favorites/{available['id']}", token=buyer_token)
        self.call(
            "POST",
            f"/inquiries/{available['id']}",
            {"message": "Can I tour this home?"},
            buyer_token,
        )

        seller_status, seller_stats = self.call(
            "GET",
            "/properties/my/stats",
            token=seller_token,
        )
        buyer_status, buyer_stats = self.call(
            "GET",
            "/properties/my/stats",
            token=buyer_token,
        )
        engagement_status, engagement = self.call(
            "GET",
            "/properties/my/engagement",
            token=seller_token,
        )
        buyer_engagement_status, buyer_engagement = self.call(
            "GET",
            "/properties/my/engagement",
            token=buyer_token,
        )

        self.assertEqual(seller_status, 200)
        self.assertEqual(
            seller_stats,
            {
                "total_listings": 2,
                "available_listings": 1,
                "unavailable_listings": 1,
                "favorites_received": 1,
                "inquiries_received": 1,
                "pending_inquiries": 1,
            },
        )
        self.assertEqual(buyer_status, 200)
        self.assertEqual(
            buyer_stats,
            {
                "total_listings": 0,
                "available_listings": 0,
                "unavailable_listings": 0,
                "favorites_received": 0,
                "inquiries_received": 0,
                "pending_inquiries": 0,
            },
        )
        self.assertEqual(engagement_status, 200)
        self.assertEqual(
            engagement,
            [
                {
                    "property_id": available["id"],
                    "favorites": 1,
                    "inquiries": 1,
                    "pending_inquiries": 1,
                },
                {
                    "property_id": available["id"] + 1,
                    "favorites": 0,
                    "inquiries": 0,
                    "pending_inquiries": 0,
                },
            ],
        )
        self.assertEqual(buyer_engagement_status, 200)
        self.assertEqual(buyer_engagement, [])

    def test_single_property_favorite_status_is_buyer_scoped(self):
        _seller, seller_token = self.register_and_login(
            "Favorite Status Seller", "favorite-status-seller@example.com"
        )
        _first_buyer, first_token = self.register_and_login(
            "First Favorite Buyer", "first-favorite-buyer@example.com"
        )
        _second_buyer, second_token = self.register_and_login(
            "Second Favorite Buyer", "second-favorite-buyer@example.com"
        )
        _create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Favorite Status Home",
                "price": 225000,
                "location": "Santo Domingo",
                "property_type": "Apartment",
                "bedrooms": 2,
                "status": "available",
            },
            seller_token,
        )
        property_path = f"/favorites/{property_item['id']}"

        self.call("POST", property_path, token=first_token)
        first_status, first = self.call("GET", f"{property_path}/status", token=first_token)
        second_status, second = self.call("GET", f"{property_path}/status", token=second_token)
        self.call("DELETE", property_path, token=first_token)
        removed_status, removed = self.call("GET", f"{property_path}/status", token=first_token)

        self.assertEqual(first_status, 200)
        self.assertEqual(first, {"is_favorite": True})
        self.assertEqual(second_status, 200)
        self.assertEqual(second, {"is_favorite": False})
        self.assertEqual(removed_status, 200)
        self.assertEqual(removed, {"is_favorite": False})

    def test_inquiry_pages_filter_count_paginate_and_isolate_users(self):
        _seller, seller_token = self.register_and_login(
            "Paged Inquiry Seller", "paged-inquiry-seller@example.com"
        )
        _buyer, buyer_token = self.register_and_login(
            "Paged Inquiry Buyer", "paged-inquiry-buyer@example.com"
        )
        _other, other_token = self.register_and_login(
            "Other Inquiry Buyer", "other-inquiry-buyer@example.com"
        )
        inquiries = []
        for index in range(5):
            _property_status, property_item = self.call(
                "POST",
                "/properties/",
                {
                    "title": f"Paged Inquiry Home {index}",
                    "price": 180000 + index,
                    "location": "Santo Domingo",
                    "property_type": "Apartment",
                    "bedrooms": 2,
                    "status": "available",
                },
                seller_token,
            )
            _inquiry_status, inquiry = self.call(
                "POST",
                f"/inquiries/{property_item['id']}",
                {"message": f"Question {index}"},
                buyer_token,
            )
            inquiries.append(inquiry)

        self.call(
            "PATCH",
            f"/inquiries/{inquiries[0]['id']}/status",
            {"status": "accepted"},
            seller_token,
        )
        self.call(
            "PATCH",
            f"/inquiries/{inquiries[1]['id']}/status",
            {"status": "rejected"},
            seller_token,
        )
        self.call(
            "PATCH",
            f"/inquiries/{inquiries[2]['id']}/cancel",
            token=buyer_token,
        )

        sent_status, sent_page = self.call(
            "GET", "/inquiries/sent/page?status=pending&page=1&page_size=1", token=buyer_token
        )
        property_status, property_page = self.call(
            "GET",
            f"/inquiries/received/page?property_id={inquiries[0]['property_id']}",
            token=seller_token,
        )
        other_status, other_page = self.call(
            "GET", "/inquiries/sent/page", token=other_token
        )

        self.assertEqual(sent_status, 200)
        self.assertEqual(sent_page["total"], 2)
        self.assertEqual(sent_page["page"], 1)
        self.assertEqual(sent_page["page_size"], 1)
        self.assertEqual(sent_page["total_pages"], 2)
        self.assertEqual(len(sent_page["items"]), 1)
        self.assertEqual(sent_page["items"][0]["status"], "pending")
        self.assertEqual(sent_page["counts"], {
            "all": 5,
            "pending": 2,
            "accepted": 1,
            "rejected": 1,
            "cancelled": 1,
        })
        self.assertEqual(property_status, 200)
        self.assertEqual(property_page["total"], 1)
        self.assertEqual(property_page["counts"]["accepted"], 1)
        self.assertEqual(property_page["items"][0]["id"], inquiries[0]["id"])
        self.assertEqual(other_status, 200)
        self.assertEqual(other_page["total"], 0)
        self.assertEqual(other_page["items"], [])

    def test_authenticated_image_upload_can_be_used_on_property(self):
        _seller, seller_token = self.register_and_login(
            "Image Seller",
            "image-seller@example.com",
        )
        png_data = valid_png_bytes()

        unauthenticated_status, _unauthenticated_body = self.call(
            "POST",
            "/uploads/property-images",
            {
                "filename": "home.png",
                "content_type": "image/png",
                "data": base64.b64encode(png_data).decode(),
            },
        )
        upload_status, upload = self.call(
            "POST",
            "/uploads/property-images",
            {
                "filename": "home.png",
                "content_type": "image/png",
                "data": base64.b64encode(png_data).decode(),
            },
            seller_token,
        )
        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Uploaded Image Home",
                "image_url": upload["image_url"],
                "price": 275000,
                "location": "Austin, Texas",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )

        saved_name = upload["image_url"].rsplit("/", 1)[-1]
        saved_path = os.path.join(self.upload_directory.name, saved_name)
        attached_delete_status, attached_delete_error = self.call(
            "DELETE",
            f"/uploads/property-images/{saved_name}",
            token=seller_token,
        )
        self.assertEqual(unauthenticated_status, 401)
        self.assertEqual(upload_status, 200)
        self.assertTrue(upload["image_url"].startswith("/uploads/property-images/"))
        self.assertTrue(os.path.isfile(saved_path))
        self.assertEqual(
            [name for name in os.listdir(self.upload_directory.name) if name.endswith(".tmp")],
            [],
        )
        with open(saved_path, "rb") as saved_image:
            self.assertEqual(saved_image.read(), png_data)
        self.assertEqual(create_status, 200)
        self.assertEqual(property_item["image_url"], upload["image_url"])
        self.assertEqual(attached_delete_status, 409)
        self.assertIn("attached", attached_delete_error["detail"])
        self.assertTrue(os.path.isfile(saved_path))

    def test_image_upload_rejects_fake_or_oversized_files(self):
        _seller, seller_token = self.register_and_login(
            "Safe Upload Seller",
            "safe-upload@example.com",
        )

        fake_status, fake_error = self.call(
            "POST",
            "/uploads/property-images",
            {
                "filename": "fake.png",
                "content_type": "image/png",
                "data": base64.b64encode(b"this is not a png").decode(),
            },
            seller_token,
        )
        corrupt_status, corrupt_error = self.call(
            "POST",
            "/uploads/property-images",
            {
                "filename": "corrupt.png",
                "content_type": "image/png",
                "data": base64.b64encode(
                    b"\x89PNG\r\n\x1a\ncorrupt-payload"
                ).decode(),
            },
            seller_token,
        )
        with patch("backend.routes.uploads.MAX_IMAGE_BYTES", new=8):
            oversized_status, oversized_error = self.call(
                "POST",
                "/uploads/property-images",
                {
                    "filename": "large.png",
                    "content_type": "image/png",
                    "data": base64.b64encode(b"\x89PNG\r\n\x1a\nextra").decode(),
                },
                seller_token,
            )

        self.assertEqual(fake_status, 400)
        self.assertIn("do not match", fake_error["detail"])
        self.assertEqual(corrupt_status, 400)
        self.assertIn("corrupt", corrupt_error["detail"])
        self.assertEqual(oversized_status, 413)
        self.assertIn("5 MB", oversized_error["detail"])

    def test_only_upload_owner_can_remove_an_unused_image(self):
        owner, owner_token = self.register_and_login(
            "Upload Owner",
            "upload-owner@example.com",
        )
        _other_user, other_token = self.register_and_login(
            "Other Upload User",
            "other-upload@example.com",
        )
        png_data = valid_png_bytes()
        upload_status, upload = self.call(
            "POST",
            "/uploads/property-images",
            {
                "filename": "unused.png",
                "content_type": "image/png",
                "data": base64.b64encode(png_data).decode(),
            },
            owner_token,
        )
        image_name = upload["image_url"].rsplit("/", 1)[-1]
        image_path = os.path.join(self.upload_directory.name, image_name)

        forbidden_status, _forbidden = self.call(
            "DELETE",
            f"/uploads/property-images/{image_name}",
            token=other_token,
        )
        delete_status, delete_body = self.call(
            "DELETE",
            f"/uploads/property-images/{image_name}",
            token=owner_token,
        )

        self.assertEqual(upload_status, 200)
        self.assertTrue(image_name.startswith(f"{owner['id']}_"))
        self.assertEqual(forbidden_status, 403)
        self.assertEqual(delete_status, 204)
        self.assertIsNone(delete_body)
        self.assertFalse(os.path.exists(image_path))

    def test_property_creation_rejects_invalid_values(self):
        _seller, seller_token = self.register_and_login(
            "Validation Seller",
            "validation-seller@example.com",
        )
        valid_property = {
            "title": "Valid Property",
            "price": 250000,
            "location": "Miami, Florida",
            "property_type": "House",
            "bedrooms": 3,
            "status": "available",
        }

        invalid_payloads = (
            {**valid_property, "title": "   "},
            {**valid_property, "location": "  "},
            {**valid_property, "price": 0},
            {**valid_property, "bedrooms": -1},
            {**valid_property, "bathrooms": -1},
            {**valid_property, "square_feet": -1},
            {**valid_property, "property_type": "Castle"},
            {**valid_property, "listing_type": "lease-to-own"},
            {**valid_property, "amenities": ["Helipad"]},
            {**valid_property, "status": "maybe"},
            {**valid_property, "image_url": "not-a-url"},
            {**valid_property, "image_url": "", "image_urls": []},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                status, _body = self.call(
                    "POST",
                    "/properties/",
                    payload,
                    seller_token,
                )
                self.assertEqual(status, 422)

    def test_property_supports_multiple_images_with_first_as_cover(self):
        _seller, seller_token = self.register_and_login(
            "Gallery Seller",
            "gallery-seller@example.com",
        )
        image_urls = [
            "https://images.example.com/front.jpg",
            "https://images.example.com/kitchen.jpg",
            "https://images.example.com/backyard.jpg",
        ]
        status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Gallery Home",
                "currency": "DOP",
                "image_urls": image_urls,
                "price": 525000,
                "location": "Denver, Colorado",
                "property_type": "House",
                "bedrooms": 4,
                "status": "available",
            },
            seller_token,
        )

        self.assertEqual(status, 200)
        self.assertEqual(property_item["image_url"], image_urls[0])
        self.assertEqual(property_item["image_urls"], image_urls)
        self.assertEqual(property_item["currency"], "DOP")
        self.assertEqual(property_item["updated_at"], property_item["created_at"])

        reordered_images = [image_urls[2], image_urls[0]]
        update_status, updated_property = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {
                "title": "Updated Gallery Home",
                "currency": "DOP",
                "image_urls": reordered_images,
                "price": 525000,
                "location": "Denver, Colorado",
                "property_type": "House",
                "bedrooms": 4,
                "status": "available",
            },
            seller_token,
        )

        self.assertEqual(update_status, 200)
        self.assertEqual(updated_property["image_url"], reordered_images[0])
        self.assertEqual(updated_property["currency"], "DOP")
        self.assertGreater(
            updated_property["updated_at"],
            updated_property["created_at"],
        )

        empty_update_status, _empty_update = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {
                "title": "Image-less Gallery Home",
                "image_url": "",
                "image_urls": [],
                "price": 525000,
                "location": "Denver, Colorado",
                "property_type": "House",
                "bedrooms": 4,
                "status": "available",
            },
            seller_token,
        )
        current_status, current_property = self.call(
            "GET",
            f"/properties/{property_item['id']}",
        )

        self.assertEqual(empty_update_status, 422)
        self.assertEqual(current_status, 200)
        self.assertEqual(current_property["image_urls"], reordered_images)

        currency_search_status, currency_search = self.call(
            "GET",
            "/properties/search?currency=DOP",
        )
        self.assertEqual(currency_search_status, 200)
        self.assertEqual([item["id"] for item in currency_search], [property_item["id"]])
        self.assertEqual(updated_property["image_urls"], reordered_images)

    def test_property_search_filters_and_validates_price_range(self):
        _seller, seller_token = self.register_and_login(
            "Search Seller",
            "search-seller@example.com",
        )

        for title, price, location, property_type, listing_type, bedrooms, bathrooms, square_feet in (
            ("Miami House", 300000, "Miami, Florida", "House", "sale", 3, 3, 2100),
            ("Orlando Condo", 2200, "Orlando, Florida", "Condo", "rent", 2, 1, 900),
        ):
            status, _property = self.call(
                "POST",
                "/properties/",
                {
                    "title": title,
                    "price": price,
                    "location": location,
                    "property_type": property_type,
                    "listing_type": listing_type,
                    "amenities": ["Pool", "Garage"] if title == "Miami House" else ["Gym", "Balcony"],
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "square_feet": square_feet,
                    "status": "available",
                },
                seller_token,
            )
            self.assertEqual(status, 200)

        search_status, results = self.call(
            "GET",
            "/properties/search?location=miami&min_price=250000&currency=USD&bedrooms=3&bathrooms=2&min_square_feet=1500",
        )
        range_status, range_error = self.call(
            "GET",
            "/properties/search?min_price=500000&max_price=100000&currency=USD",
        )
        negative_status, _negative_error = self.call(
            "GET",
            "/properties/search?min_price=-1",
        )
        negative_bathrooms_status, _negative_bathrooms_error = self.call(
            "GET",
            "/properties/search?bathrooms=-1",
        )
        negative_size_status, _negative_size_error = self.call(
            "GET",
            "/properties/search?min_square_feet=-1",
        )
        rent_status, rent_results = self.call(
            "GET",
            "/properties/search?listing_type=rent",
        )
        amenity_status, amenity_results = self.call(
            "GET",
            "/properties/search?amenity=Pool",
        )

        self.assertEqual(search_status, 200)
        self.assertEqual([item["title"] for item in results], ["Miami House"])
        self.assertEqual(range_status, 400)
        self.assertEqual(
            range_error["detail"],
            "Minimum price cannot be greater than maximum price",
        )
        self.assertEqual(negative_status, 422)
        self.assertEqual(negative_bathrooms_status, 422)
        self.assertEqual(negative_size_status, 422)
        self.assertEqual(rent_status, 200)
        self.assertEqual([item["title"] for item in rent_results], ["Orlando Condo"])
        self.assertEqual(rent_results[0]["listing_type"], "rent")
        self.assertEqual(amenity_status, 200)
        self.assertEqual([item["title"] for item in amenity_results], ["Miami House"])
        self.assertEqual(amenity_results[0]["amenities"], ["Pool", "Garage"])

        all_status, all_properties = self.call(
            "GET",
            "/properties/",
        )
        high_price_status, high_price_properties = self.call(
            "GET",
            "/properties/search?sort_by=price_high&currency=USD",
        )
        invalid_sort_status, _invalid_sort_error = self.call(
            "GET",
            "/properties/search?sort_by=oldest",
        )

        self.assertEqual(all_status, 200)
        self.assertEqual(
            [item["title"] for item in all_properties],
            ["Orlando Condo", "Miami House"],
        )
        miami_property = next(item for item in all_properties if item["title"] == "Miami House")
        reference_status, reference_results = self.call(
            "GET",
            f"/properties/search?reference=PM-{miami_property['id']:06d}",
        )
        self.assertEqual(reference_status, 200)
        self.assertEqual([item["id"] for item in reference_results], [miami_property["id"]])
        self.assertEqual(high_price_status, 200)
        self.assertEqual(
            [item["title"] for item in high_price_properties],
            ["Miami House", "Orlando Condo"],
        )
        self.assertEqual(invalid_sort_status, 422)

    def test_profile_and_password_updates_validate_input(self):
        invalid_registration_status, _invalid_registration = self.call(
            "POST",
            "/users/",
            {
                "name": "   ",
                "email": "not-an-email",
                "password": "secure-password",
            },
        )
        user, token = self.register_and_login(
            "Account User",
            "account-user@example.com",
        )

        invalid_email_status, _invalid_email = self.call(
            "PUT",
            "/users/me",
            {"name": "Account User", "email": "not-an-email"},
            token,
        )
        short_password_status, _short_password = self.call(
            "PATCH",
            "/users/me/password",
            {
                "current_password": "secure-password",
                "new_password": "short",
            },
            token,
        )
        profile_status, profile = self.call(
            "PUT",
            "/users/me",
            {
                "name": "Updated Account User",
                "email": "UPDATED@example.com",
                "current_password": "secure-password",
            },
            token,
        )
        password_status, password_result = self.call(
            "PATCH",
            "/users/me/password",
            {
                "current_password": "secure-password",
                "new_password": "new-secure-password",
            },
            token,
        )
        revoked_token_status, _revoked_token = self.call(
            "GET", "/users/me", token=token
        )
        replacement_token_status, replacement_user = self.call(
            "GET",
            "/users/me",
            token=password_result.get("access_token"),
        )
        old_login_status, _old_login = self.call(
            "POST",
            "/users/login",
            {
                "email": "updated@example.com",
                "password": "secure-password",
            },
        )
        new_login_status, _new_login = self.call(
            "POST",
            "/users/login",
            {
                "email": "updated@example.com",
                "password": "new-secure-password",
            },
        )

        self.assertEqual(invalid_registration_status, 422)
        self.assertEqual(invalid_email_status, 422)
        self.assertEqual(short_password_status, 422)
        self.assertEqual(profile_status, 200)
        self.assertEqual(profile["id"], user["id"])
        self.assertEqual(profile["name"], "Updated Account User")
        self.assertEqual(profile["email"], "updated@example.com")
        self.assertEqual(password_status, 200)
        self.assertEqual(
            password_result["message"],
            "Password changed successfully",
        )
        self.assertEqual(revoked_token_status, 401)
        self.assertEqual(replacement_token_status, 200)
        self.assertEqual(replacement_user["id"], user["id"])
        self.assertEqual(old_login_status, 401)
        self.assertEqual(new_login_status, 200)

    def test_email_change_requires_current_password_without_blocking_name_edits(self):
        user, token = self.register_and_login(
            "Profile User",
            "profile-user@example.com",
        )

        name_status, name_result = self.call(
            "PUT",
            "/users/me",
            {
                "name": "Safer Profile User",
                "email": "profile-user@example.com",
            },
            token,
        )
        missing_status, missing_result = self.call(
            "PUT",
            "/users/me",
            {
                "name": "Safer Profile User",
                "email": "redirected@example.com",
            },
            token,
        )
        wrong_status, wrong_result = self.call(
            "PUT",
            "/users/me",
            {
                "name": "Safer Profile User",
                "email": "redirected@example.com",
                "current_password": "wrong-password",
            },
            token,
        )
        unchanged_status, unchanged_user = self.call(
            "GET",
            "/users/me",
            token=token,
        )
        changed_status, changed_user = self.call(
            "PUT",
            "/users/me",
            {
                "name": "Safer Profile User",
                "email": "redirected@example.com",
                "current_password": "secure-password",
            },
            token,
        )

        self.assertEqual(name_status, 200)
        self.assertEqual(name_result["id"], user["id"])
        self.assertEqual(name_result["name"], "Safer Profile User")
        self.assertEqual(missing_status, 400)
        self.assertEqual(
            missing_result["detail"],
            "Current password is required to change your email",
        )
        self.assertEqual(wrong_status, 400)
        self.assertEqual(wrong_result["detail"], "Current password is incorrect")
        self.assertEqual(unchanged_status, 200)
        self.assertEqual(unchanged_user["email"], "profile-user@example.com")
        self.assertEqual(changed_status, 200)
        self.assertEqual(changed_user["email"], "redirected@example.com")

    def test_inquiry_unread_counts_are_participant_scoped_and_markable(self):
        seller, seller_token = self.register_and_login(
            "Unread Seller", "unread-seller@example.com"
        )
        _buyer, buyer_token = self.register_and_login(
            "Unread Buyer", "unread-buyer@example.com"
        )
        _outsider, outsider_token = self.register_and_login(
            "Unread Outsider", "unread-outsider@example.com"
        )
        _property_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Unread Conversation Home",
                "price": 195000,
                "location": "Santiago",
                "property_type": "Apartment",
                "bedrooms": 2,
                "status": "available",
            },
            seller_token,
        )
        _inquiry_status, inquiry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Can I see it this week?"},
            buyer_token,
        )

        _buyer_zero_status, buyer_zero = self.call(
            "GET", "/inquiries/unread-count", token=buyer_token
        )
        seller_one_status, seller_one = self.call(
            "GET", "/inquiries/unread-count", token=seller_token
        )
        page_status, received_page = self.call(
            "GET", "/inquiries/received/page", token=seller_token
        )
        mark_status, _mark_body = self.call(
            "PATCH",
            "/inquiries/read",
            {"receipts": [{
                "inquiry_id": inquiry["id"],
                "read_through_at": received_page["items"][0]["read_through_at"],
            }]},
            seller_token,
        )
        _seller_zero_status, seller_zero = self.call(
            "GET", "/inquiries/unread-count", token=seller_token
        )
        self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "Thursday afternoon would work."},
            buyer_token,
        )
        _seller_reply_status, seller_after_buyer_message = self.call(
            "GET", "/inquiries/unread-count", token=seller_token
        )
        self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "Thursday at 2 PM is available."},
            seller_token,
        )
        buyer_unread_status, buyer_unread = self.call(
            "GET", "/inquiries/unread-count", token=buyer_token
        )
        sent_page_status, sent_page = self.call(
            "GET", "/inquiries/sent/page", token=buyer_token
        )
        outsider_mark_status, _outsider_mark = self.call(
            "PATCH",
            "/inquiries/read",
            {"receipts": [{
                "inquiry_id": inquiry["id"],
                "read_through_at": sent_page["items"][0]["read_through_at"],
            }]},
            outsider_token,
        )

        self.assertEqual(buyer_zero["unread_count"], 0)
        self.assertEqual(seller_one_status, 200)
        self.assertEqual(seller_one["unread_count"], 1)
        self.assertEqual(page_status, 200)
        self.assertEqual(received_page["items"][0]["unread_count"], 1)
        self.assertEqual(mark_status, 204)
        self.assertEqual(seller_zero["unread_count"], 0)
        self.assertEqual(seller_after_buyer_message["unread_count"], 1)
        self.assertEqual(buyer_unread_status, 200)
        self.assertEqual(buyer_unread["unread_count"], 1)
        self.assertEqual(sent_page_status, 200)
        self.assertEqual(sent_page["items"][0]["unread_count"], 1)
        self.assertEqual(outsider_mark_status, 403)

    def test_read_receipt_does_not_clear_a_message_newer_than_the_delivered_page(self):
        _seller, seller_token = self.register_and_login(
            "Receipt Seller", "receipt-seller@example.com"
        )
        _buyer, buyer_token = self.register_and_login(
            "Receipt Buyer", "receipt-buyer@example.com"
        )
        _property_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Receipt Boundary Home",
                "price": 225000,
                "location": "La Vega",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        _inquiry_status, inquiry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "May I arrange a viewing?"},
            buyer_token,
        )
        _page_status, delivered_page = self.call(
            "GET", "/inquiries/received/page", token=seller_token
        )
        delivered_boundary = delivered_page["items"][0]["read_through_at"]

        self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "I can also visit Saturday morning."},
            buyer_token,
        )
        stale_receipt_status, _stale_receipt = self.call(
            "PATCH",
            "/inquiries/read",
            {"receipts": [{
                "inquiry_id": inquiry["id"],
                "read_through_at": delivered_boundary,
            }]},
            seller_token,
        )
        _still_unread_status, still_unread = self.call(
            "GET", "/inquiries/unread-count", token=seller_token
        )
        _fresh_page_status, fresh_page = self.call(
            "GET", "/inquiries/received/page", token=seller_token
        )
        fresh_receipt_status, _fresh_receipt = self.call(
            "PATCH",
            "/inquiries/read",
            {"receipts": [{
                "inquiry_id": inquiry["id"],
                "read_through_at": fresh_page["items"][0]["read_through_at"],
            }]},
            seller_token,
        )
        _cleared_status, cleared = self.call(
            "GET", "/inquiries/unread-count", token=seller_token
        )

        self.assertEqual(stale_receipt_status, 204)
        self.assertEqual(still_unread["unread_count"], 1)
        self.assertEqual(fresh_receipt_status, 204)
        self.assertEqual(cleared["unread_count"], 0)

    def test_buyer_and_seller_can_message_from_the_inquiry_thread(self):
        seller, seller_token = self.register_and_login(
            "Thread Seller", "thread-seller@example.com"
        )
        _buyer, buyer_token = self.register_and_login(
            "Thread Buyer", "thread-buyer@example.com"
        )
        _outsider, outsider_token = self.register_and_login(
            "Thread Outsider", "thread-outsider@example.com"
        )
        _property_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Conversation Home",
                "price": 250000,
                "location": "Santo Domingo",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        _inquiry_status, inquiry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Is it available?"},
            buyer_token,
        )

        buyer_message_key = str(uuid4())
        buyer_message_status, _buyer_message = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "I can visit tomorrow afternoon."},
            buyer_token,
            idempotency_key=buyer_message_key,
        )
        retry_status, _retried_message = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "I can visit tomorrow afternoon."},
            buyer_token,
            idempotency_key=buyer_message_key,
        )
        conflict_status, _conflict = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "Different content must not replace it."},
            buyer_token,
            idempotency_key=buyer_message_key,
        )
        seller_message_status, _seller_message = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "Tomorrow at 3 PM works."},
            seller_token,
        )
        outsider_status, _outsider_error = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "I should not see this."},
            outsider_token,
        )
        page_status, page = self.call(
            "GET", "/inquiries/sent/page", token=buyer_token
        )
        self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/status",
            {"status": "rejected"},
            seller_token,
        )
        closed_status, _closed_error = self.call(
            "POST",
            f"/inquiries/{inquiry['id']}/messages",
            {"message": "This should not be added."},
            buyer_token,
        )

        conversation = page["items"][0]["conversation_messages"]
        self.assertEqual(buyer_message_status, 200)
        self.assertEqual(retry_status, 200)
        self.assertEqual(conflict_status, 409)
        self.assertEqual(seller_message_status, 200)
        self.assertEqual(outsider_status, 403)
        self.assertEqual(page_status, 200)
        self.assertEqual(
            [message["body"] for message in conversation],
            [
                "Is it available?",
                "I can visit tomorrow afternoon.",
                "Tomorrow at 3 PM works.",
            ],
        )
        self.assertEqual(
            [message["sender_role"] for message in conversation],
            ["buyer", "buyer", "seller"],
        )
        self.assertEqual(conversation[-1]["sender_name"], seller["name"])
        self.assertEqual(closed_status, 400)

    def test_listing_reports_are_private_retry_safe_and_keep_review_evidence(self):
        seller, seller_token = self.register_and_login(
            "Report Seller",
            "report-seller@example.com",
        )
        _buyer, buyer_token = self.register_and_login(
            "Report Buyer",
            "report-buyer@example.com",
        )
        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Listing Needing Review",
                "price": 95000,
                "location": "Santo Domingo, Dominican Republic",
                "property_type": "Apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "status": "available",
            },
            seller_token,
        )
        property_id = property_item["id"]
        report_key = str(uuid4())

        guest_status, _guest_error = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "suspected_scam", "details": "Payment requested off platform."},
            idempotency_key=report_key,
        )
        missing_key_status, _missing_key_error = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "suspected_scam", "details": "Payment requested off platform."},
            buyer_token,
        )
        owner_status, owner_error = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "other", "details": "Owner report must be rejected."},
            seller_token,
            idempotency_key=str(uuid4()),
        )
        invalid_status, _invalid_error = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "not-a-valid-reason", "details": "Invalid category."},
            buyer_token,
            idempotency_key=str(uuid4()),
        )
        report_status, report = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {
                "reason": "suspected_scam",
                "details": "  Payment requested off platform.  ",
            },
            buyer_token,
            idempotency_key=report_key,
        )
        replay_status, replay = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "other", "details": "A retry must not replace evidence."},
            buyer_token,
            idempotency_key=report_key,
        )
        duplicate_status, duplicate = self.call(
            "POST",
            f"/reports/properties/{property_id}",
            {"reason": "duplicate_listing", "details": "Second submission."},
            buyer_token,
            idempotency_key=str(uuid4()),
        )
        delete_status, _deleted_property = self.call(
            "DELETE",
            f"/properties/{property_id}",
            token=seller_token,
            property_version=property_item["version"],
        )
        stored_report = self.session.get(ListingReportDB, report["id"])

        self.assertEqual(create_status, 200)
        self.assertEqual(guest_status, 401)
        self.assertEqual(missing_key_status, 422)
        self.assertEqual(owner_status, 400)
        self.assertEqual(owner_error["detail"], "You cannot report your own property")
        self.assertEqual(invalid_status, 422)
        self.assertEqual(report_status, 200)
        self.assertEqual(report["listing_id"], property_id)
        self.assertEqual(report["listing_title"], "Listing Needing Review")
        self.assertEqual(report["reason"], "suspected_scam")
        self.assertEqual(report["details"], "Payment requested off platform.")
        self.assertEqual(report["status"], "submitted")
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay, report)
        self.assertEqual(duplicate_status, 200)
        self.assertEqual(duplicate, report)
        self.assertEqual(delete_status, 200)
        self.assertIsNotNone(stored_report)
        self.assertIsNone(stored_report.property_id)
        self.assertEqual(stored_report.listing_id, property_id)
        self.assertEqual(stored_report.listing_owner_id, seller["id"])

    def test_report_history_is_private_and_hides_internal_review_details(self):
        _seller, seller_token = self.register_and_login(
            "History Seller",
            "history-seller@example.com",
        )
        _buyer_one, buyer_one_token = self.register_and_login(
            "History Buyer One",
            "history-buyer-one@example.com",
        )
        _buyer_two, buyer_two_token = self.register_and_login(
            "History Buyer Two",
            "history-buyer-two@example.com",
        )
        admin, admin_token = self.register_and_login(
            "History Admin",
            "history-admin@example.com",
        )
        _create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "History Listing Snapshot",
                "price": 175000,
                "location": "La Vega, Dominican Republic",
                "property_type": "House",
                "bedrooms": 3,
                "bathrooms": 2,
                "status": "available",
            },
            seller_token,
        )
        first_status, first_report = self.call(
            "POST",
            f"/reports/properties/{property_item['id']}",
            {"reason": "suspected_scam", "details": "Unusual payment request."},
            buyer_one_token,
            idempotency_key=str(uuid4()),
        )
        second_status, second_report = self.call(
            "POST",
            f"/reports/properties/{property_item['id']}",
            {"reason": "already_unavailable", "details": "Seller said it was unavailable."},
            buyer_two_token,
            idempotency_key=str(uuid4()),
        )

        with patch.dict(os.environ, {"ADMIN_USER_IDS": str(admin["id"])}):
            _queue_status, queue = self.call(
                "GET",
                "/reports/admin?status=submitted",
                token=admin_token,
            )
            first_admin_report = next(
                item for item in queue["items"] if item["id"] == first_report["id"]
            )
            resolved_status, _resolved = self.call(
                "PATCH",
                f"/reports/admin/{first_report['id']}",
                {
                    "status": "resolved",
                    "moderator_note": "Internal note must never be returned to the reporter.",
                },
                admin_token,
                report_version=first_admin_report["version"],
            )

        guest_status, _guest = self.call("GET", "/reports/mine")
        invalid_page_status, _invalid_page = self.call(
            "GET",
            "/reports/mine?page=0",
            token=buyer_one_token,
        )
        first_history_status, first_history = self.call(
            "GET",
            "/reports/mine?page=1&page_size=1",
            token=buyer_one_token,
        )
        second_history_status, second_history = self.call(
            "GET",
            "/reports/mine",
            token=buyer_two_token,
        )
        delete_status, _deleted = self.call(
            "DELETE",
            f"/properties/{property_item['id']}",
            token=seller_token,
            property_version=property_item["version"],
        )
        removed_history_status, removed_history = self.call(
            "GET",
            "/reports/mine",
            token=buyer_one_token,
        )

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(resolved_status, 200)
        self.assertEqual(guest_status, 401)
        self.assertEqual(invalid_page_status, 422)
        self.assertEqual(first_history_status, 200)
        self.assertEqual(first_history["total"], 1)
        self.assertEqual(first_history["page_size"], 1)
        self.assertEqual(first_history["items"][0]["id"], first_report["id"])
        self.assertEqual(first_history["items"][0]["status"], "resolved")
        self.assertEqual(first_history["items"][0]["property_id"], property_item["id"])
        self.assertNotIn("moderator_note", first_history["items"][0])
        self.assertNotIn("reviewer_name", first_history["items"][0])
        self.assertNotIn("listing_owner_id", first_history["items"][0])
        self.assertEqual(second_history_status, 200)
        self.assertEqual(second_history["total"], 1)
        self.assertEqual(second_history["items"][0]["id"], second_report["id"])
        self.assertEqual(delete_status, 200)
        self.assertEqual(removed_history_status, 200)
        self.assertIsNone(removed_history["items"][0]["property_id"])
        self.assertEqual(
            removed_history["items"][0]["listing_title"],
            "History Listing Snapshot",
        )

    def test_only_configured_admins_can_review_reports_without_stale_overwrites(self):
        seller, seller_token = self.register_and_login(
            "Moderation Seller",
            "moderation-seller@example.com",
        )
        _buyer, buyer_token = self.register_and_login(
            "Moderation Buyer",
            "moderation-buyer@example.com",
        )
        admin, admin_token = self.register_and_login(
            "Safety Admin",
            "safety-admin@example.com",
        )
        _create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Moderation Queue Listing",
                "price": 125000,
                "location": "Santiago, Dominican Republic",
                "property_type": "House",
                "bedrooms": 3,
                "bathrooms": 2,
                "status": "available",
            },
            seller_token,
        )
        report_status, report = self.call(
            "POST",
            f"/reports/properties/{property_item['id']}",
            {"reason": "misleading_information", "details": "The location appears incorrect."},
            buyer_token,
            idempotency_key=str(uuid4()),
        )

        with patch.dict(
            os.environ,
            {"ADMIN_USER_IDS": f" {admin['id']} "},
        ):
            denied_status, denied = self.call(
                "GET",
                "/reports/admin/access",
                token=buyer_token,
            )
            access_status, access = self.call(
                "GET",
                "/reports/admin/access",
                token=admin_token,
            )
            queue_status, queue = self.call(
                "GET",
                "/reports/admin?status=submitted&page=1&page_size=10",
                token=admin_token,
            )
            missing_version_status, _missing_version = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "reviewing", "moderator_note": ""},
                admin_token,
            )
            missing_note_status, missing_note = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "resolved", "moderator_note": ""},
                admin_token,
                report_version=1,
            )
            reviewing_status, reviewing = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "reviewing", "moderator_note": "Checking the listing details."},
                admin_token,
                report_version=1,
            )
            retry_status, retry = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "reviewing", "moderator_note": "Checking the listing details."},
                admin_token,
                report_version=1,
            )
            stale_status, stale = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "dismissed", "moderator_note": "Stale decision."},
                admin_token,
                report_version=1,
            )
            resolved_status, resolved = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {
                    "status": "resolved",
                    "moderator_note": "Confirmed the listing needs operator follow-up.",
                },
                admin_token,
                report_version=reviewing["version"],
            )
            reopen_status, reopen = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}",
                {"status": "dismissed", "moderator_note": "Conflicting terminal decision."},
                admin_token,
                report_version=resolved["version"],
            )
            resolved_queue_status, resolved_queue = self.call(
                "GET",
                "/reports/admin?status=resolved",
                token=admin_token,
            )

        self.assertEqual(report_status, 200)
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied["detail"], "Administrator access required")
        self.assertEqual(access_status, 200)
        self.assertEqual(access, {"is_admin": True})
        self.assertEqual(queue_status, 200)
        self.assertEqual(queue["total"], 1)
        self.assertEqual(queue["counts"]["submitted"], 1)
        self.assertEqual(queue["items"][0]["reporter_name"], "Moderation Buyer")
        self.assertEqual(queue["items"][0]["listing_owner_id"], seller["id"])
        self.assertEqual(missing_version_status, 422)
        self.assertEqual(missing_note_status, 400)
        self.assertEqual(
            missing_note["detail"],
            "Add a short review note before closing this report",
        )
        self.assertEqual(reviewing_status, 200)
        self.assertEqual(reviewing["status"], "reviewing")
        self.assertEqual(reviewing["version"], 2)
        self.assertEqual(retry_status, 200)
        self.assertEqual(retry, reviewing)
        self.assertEqual(stale_status, 409)
        self.assertIn("changed in another review session", stale["detail"])
        self.assertEqual(resolved_status, 200)
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["reviewer_name"], "Safety Admin")
        self.assertEqual(resolved["version"], 3)
        self.assertTrue(resolved["reviewed_at"])
        self.assertEqual(reopen_status, 400)
        self.assertEqual(
            reopen["detail"],
            "This safety report cannot be moved to the requested status",
        )
        self.assertEqual(resolved_queue_status, 200)
        self.assertEqual(resolved_queue["total"], 1)
        self.assertEqual(resolved_queue["counts"]["resolved"], 1)

    def test_moderator_safety_hold_hides_listing_and_blocks_new_inquiries(self):
        seller, seller_token = self.register_and_login(
            "Hold Seller",
            "hold-seller@example.com",
        )
        _buyer, buyer_token = self.register_and_login(
            "Hold Buyer",
            "hold-buyer@example.com",
        )
        admin, admin_token = self.register_and_login(
            "Hold Admin",
            "hold-admin@example.com",
        )
        _create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Safety Hold Listing",
                "description": "Original listing details.",
                "price": 215000,
                "location": "Puerto Plata, Dominican Republic",
                "property_type": "Condo",
                "bedrooms": 2,
                "bathrooms": 2,
                "status": "available",
            },
            seller_token,
        )
        report_status, report = self.call(
            "POST",
            f"/reports/properties/{property_item['id']}",
            {"reason": "suspected_scam", "details": "Please verify this listing."},
            buyer_token,
            idempotency_key=str(uuid4()),
        )

        with patch.dict(os.environ, {"ADMIN_USER_IDS": str(admin["id"])}):
            queue_status, queue = self.call("GET", "/reports/admin", token=admin_token)
            queued_report = next(item for item in queue["items"] if item["id"] == report["id"])
            denied_status, _denied = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": True},
                buyer_token,
                safety_version=1,
            )
            missing_version_status, _missing = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": True},
                admin_token,
            )
            hold_status, held = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": True},
                admin_token,
                safety_version=queued_report["listing_safety_version"],
            )
            retry_status, retry = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": True},
                admin_token,
                safety_version=queued_report["listing_safety_version"],
            )

        list_status, listings, list_headers = self.call_with_headers("GET", "/properties/")
        search_status, search_results = self.call(
            "GET",
            "/properties/search?location=Puerto%20Plata",
        )
        direct_status, direct = self.call("GET", f"/properties/{property_item['id']}")
        inquiry_status, inquiry_error = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Is this listing available?"},
            buyer_token,
            idempotency_key=str(uuid4()),
        )
        blocked_edit_status, blocked_edit = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {
                "title": "Unsafe Available Edit",
                "description": "This edit must not be saved.",
                "price": 215000,
                "location": "Puerto Plata, Dominican Republic",
                "property_type": "Condo",
                "bedrooms": 2,
                "bathrooms": 2,
                "status": "available",
            },
            seller_token,
            property_version=property_item["version"],
        )
        correction_status, corrected = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {
                "title": "Corrected Safety Hold Listing",
                "description": "Corrected listing details.",
                "price": 215000,
                "location": "Puerto Plata, Dominican Republic",
                "property_type": "Condo",
                "bedrooms": 2,
                "bathrooms": 2,
                "status": "unavailable",
            },
            seller_token,
            property_version=property_item["version"],
        )

        with patch.dict(os.environ, {"ADMIN_USER_IDS": str(admin["id"])}):
            stale_release_status, stale_release = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": False},
                admin_token,
                safety_version=1,
            )
            release_status, released = self.call(
                "PATCH",
                f"/reports/admin/{report['id']}/listing-hold",
                {"held": False},
                admin_token,
                safety_version=held["safety_version"],
            )

        available_status, available = self.call(
            "PUT",
            f"/properties/{property_item['id']}",
            {
                "title": corrected["title"],
                "description": corrected["description"],
                "price": corrected["price"],
                "location": corrected["location"],
                "property_type": corrected["property_type"],
                "bedrooms": corrected["bedrooms"],
                "bathrooms": corrected["bathrooms"],
                "status": "available",
            },
            seller_token,
            property_version=corrected["version"],
        )
        visible_status, visible_results = self.call(
            "GET",
            "/properties/search?location=Puerto%20Plata",
        )
        allowed_inquiry_status, _allowed_inquiry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Now can I ask about it?"},
            buyer_token,
            idempotency_key=str(uuid4()),
        )
        stored_property = self.session.get(PropertyDB, property_item["id"])

        self.assertEqual(report_status, 200)
        self.assertEqual(queue_status, 200)
        self.assertFalse(queued_report["listing_on_safety_hold"])
        self.assertEqual(queued_report["listing_safety_version"], 1)
        self.assertEqual(denied_status, 403)
        self.assertEqual(missing_version_status, 422)
        self.assertEqual(hold_status, 200)
        self.assertTrue(held["safety_hold"])
        self.assertEqual(held["safety_version"], 2)
        self.assertEqual(retry_status, 200)
        self.assertEqual(retry, held)
        self.assertEqual(list_status, 200)
        self.assertEqual(listings, [])
        self.assertEqual(list_headers["x-total-count"], "0")
        self.assertEqual(search_status, 200)
        self.assertEqual(search_results, [])
        self.assertEqual(direct_status, 200)
        self.assertTrue(direct["safety_hold"])
        self.assertEqual(inquiry_status, 409)
        self.assertIn("safety review", inquiry_error["detail"])
        self.assertEqual(blocked_edit_status, 409)
        self.assertIn("safety review", blocked_edit["detail"])
        self.assertEqual(correction_status, 200)
        self.assertEqual(corrected["status"], "unavailable")
        self.assertTrue(corrected["safety_hold"])
        self.assertEqual(stale_release_status, 409)
        self.assertIn("changed in another review session", stale_release["detail"])
        self.assertEqual(release_status, 200)
        self.assertFalse(released["safety_hold"])
        self.assertEqual(released["safety_version"], 3)
        self.assertEqual(available_status, 200)
        self.assertEqual(visible_status, 200)
        self.assertEqual([item["id"] for item in visible_results], [property_item["id"]])
        self.assertEqual(allowed_inquiry_status, 200)
        self.assertEqual(available["status"], "available")
        self.assertEqual(stored_property.safety_report_id, report["id"])
        self.assertEqual(stored_property.safety_updated_by_id, admin["id"])

    def test_complete_buyer_seller_marketplace_flow(self):
        seller, seller_token = self.register_and_login(
            "Flow Seller",
            "flow-seller@example.com",
        )
        buyer, buyer_token = self.register_and_login(
            "Flow Buyer",
            "flow-buyer@example.com",
        )

        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Marketplace Flow Home",
                "description": "A spacious home close to parks and schools.",
                "image_url": "https://images.example.com/flow-home.jpg",
                "price": 410000,
                "location": "Orlando, Florida",
                "property_type": "House",
                "bedrooms": 4,
                "bathrooms": 3,
                "square_feet": 2450,
                "status": "available",
            },
            seller_token,
        )
        property_id = property_item["id"]

        own_favorite_status, own_favorite_error = self.call(
            "POST",
            f"/favorites/{property_id}",
            token=seller_token,
        )

        favorite_status, favorite = self.call(
            "POST",
            f"/favorites/{property_id}",
            token=buyer_token,
        )
        inquiry_status, inquiry = self.call(
            "POST",
            f"/inquiries/{property_id}",
            {"message": "Could I schedule a viewing?"},
            buyer_token,
        )
        sent_status, sent = self.call(
            "GET",
            "/inquiries/sent",
            token=buyer_token,
        )
        received_status, received = self.call(
            "GET",
            "/inquiries/received",
            token=seller_token,
        )
        reply_status, replied = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/reply",
            {"reply": "Yes, Saturday works."},
            seller_token,
        )
        accept_status, accepted = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/status",
            {"status": "accepted"},
            seller_token,
        )

        self.assertEqual(create_status, 200)
        self.assertEqual(property_item["owner_id"], seller["id"])
        self.assertEqual(property_item["owner_name"], seller["name"].split()[0])
        self.assertEqual(
            property_item["description"],
            "A spacious home close to parks and schools.",
        )
        self.assertEqual(
            property_item["image_url"],
            "https://images.example.com/flow-home.jpg",
        )
        self.assertEqual(property_item["bathrooms"], 3)
        self.assertEqual(property_item["square_feet"], 2450)
        self.assertTrue(property_item["created_at"])
        self.assertEqual(own_favorite_status, 400)
        self.assertEqual(
            own_favorite_error["detail"],
            "You cannot favorite your own property",
        )
        self.assertEqual(favorite_status, 200)
        self.assertEqual(favorite["user_id"], buyer["id"])
        self.assertEqual(inquiry_status, 200)
        self.assertEqual(inquiry["buyer_id"], buyer["id"])
        self.assertEqual(inquiry["buyer_name"], buyer["name"])
        self.assertEqual(inquiry["seller_name"], seller["name"])
        self.assertEqual(
            inquiry["property_title"],
            "Marketplace Flow Home",
        )
        self.assertEqual(sent_status, 200)
        self.assertEqual([item["id"] for item in sent], [inquiry["id"]])
        self.assertEqual(received_status, 200)
        self.assertEqual([item["id"] for item in received], [inquiry["id"]])
        self.assertEqual(reply_status, 200)
        self.assertEqual(replied["reply"], "Yes, Saturday works.")
        self.assertEqual(accept_status, 200)
        self.assertEqual(accepted["status"], "accepted")

        delete_status, _deleted = self.call(
            "DELETE",
            f"/properties/{property_id}",
            token=seller_token,
            property_version=property_item["version"],
        )
        favorites_status, favorites = self.call(
            "GET",
            "/favorites/",
            token=buyer_token,
        )
        sent_after_status, sent_after = self.call(
            "GET",
            "/inquiries/sent",
            token=buyer_token,
        )

        self.assertEqual(delete_status, 200)
        self.assertEqual(favorites_status, 200)
        self.assertEqual(favorites, [])
        self.assertEqual(sent_after_status, 200)
        self.assertEqual(sent_after, [])

    def test_buyer_can_cancel_pending_inquiry_over_http(self):
        seller, seller_token = self.register_and_login(
            "Cancellation Seller",
            "cancellation-seller@example.com",
        )
        buyer, buyer_token = self.register_and_login(
            "Cancellation Buyer",
            "cancellation-buyer@example.com",
        )
        create_status, property_item = self.call(
            "POST",
            "/properties/",
            {
                "title": "Cancellation Test Home",
                "price": 280000,
                "location": "Sacramento, California",
                "property_type": "House",
                "bedrooms": 3,
                "status": "available",
            },
            seller_token,
        )
        inquiry_status, inquiry = self.call(
            "POST",
            f"/inquiries/{property_item['id']}",
            {"message": "Can I arrange a viewing?"},
            buyer_token,
        )

        forbidden_status, _forbidden = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/cancel",
            token=seller_token,
        )
        cancel_status, cancelled = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/cancel",
            token=buyer_token,
        )
        retry_cancel_status, retry_cancelled = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/cancel",
            token=buyer_token,
        )
        accept_status, _accept_error = self.call(
            "PATCH",
            f"/inquiries/{inquiry['id']}/status",
            {"status": "accepted"},
            seller_token,
        )
        received_status, received = self.call(
            "GET",
            "/inquiries/received",
            token=seller_token,
        )

        self.assertEqual(create_status, 200)
        self.assertEqual(inquiry_status, 200)
        self.assertEqual(inquiry["buyer_id"], buyer["id"])
        self.assertEqual(inquiry["seller_id"], seller["id"])
        self.assertTrue(inquiry["created_at"])
        self.assertTrue(inquiry["updated_at"])
        self.assertEqual(forbidden_status, 403)
        self.assertEqual(cancel_status, 200)
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(retry_cancel_status, 200)
        self.assertEqual(retry_cancelled["id"], cancelled["id"])
        self.assertTrue(cancelled["updated_at"])
        self.assertEqual(accept_status, 400)
        self.assertEqual(received_status, 200)
        self.assertEqual(received[0]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
