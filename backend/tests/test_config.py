import unittest
import warnings

from backend.config import (
    api_documentation_paths,
    database_engine_options,
    parse_admin_user_ids,
    parse_app_environment,
    parse_boolean_setting,
    parse_bounded_integer_setting,
    parse_cors_origins,
    parse_trusted_hosts,
    validate_secret_key,
    validate_production_environment,
)


class ConfigurationTests(unittest.TestCase):
    def test_bounded_integer_settings_reject_invalid_pool_limits(self):
        self.assertEqual(
            parse_bounded_integer_setting(
                "POOL", None, default=5, minimum=1, maximum=10
            ),
            5,
        )
        self.assertEqual(
            parse_bounded_integer_setting(
                "POOL", " 7 ", default=5, minimum=1, maximum=10
            ),
            7,
        )
        for value in ("zero", "0", "11"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    parse_bounded_integer_setting(
                        "POOL", value, default=5, minimum=1, maximum=10
                    )

    def test_postgresql_engine_options_bound_connections_and_waits(self):
        settings = {
            "DATABASE_POOL_SIZE": "8",
            "DATABASE_MAX_OVERFLOW": "4",
            "DATABASE_POOL_TIMEOUT_SECONDS": "12",
            "DATABASE_POOL_RECYCLE_SECONDS": "600",
            "DATABASE_CONNECT_TIMEOUT_SECONDS": "9",
        }
        options = database_engine_options(
            "postgresql+psycopg://database/habitard", settings
        )

        self.assertTrue(options["pool_pre_ping"])
        self.assertTrue(options["hide_parameters"])
        self.assertTrue(options["pool_use_lifo"])
        self.assertEqual(options["pool_size"], 8)
        self.assertEqual(options["max_overflow"], 4)
        self.assertEqual(options["pool_timeout"], 12)
        self.assertEqual(options["pool_recycle"], 600)
        self.assertEqual(options["connect_args"]["connect_timeout"], 9)
        self.assertEqual(options["connect_args"]["application_name"], "HabitaRD API")

    def test_sqlite_engine_options_do_not_receive_postgresql_pool_arguments(self):
        self.assertEqual(
            database_engine_options("sqlite:///habitard.db", {}),
            {"pool_pre_ping": True, "hide_parameters": True},
        )

    def test_application_environment_is_explicit_and_fails_closed_on_typos(self):
        self.assertEqual(parse_app_environment(None), "development")
        self.assertEqual(parse_app_environment(" TEST "), "test")
        self.assertEqual(parse_app_environment("production"), "production")
        for value in ("prod", "prodution", "staging", ""):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    parse_app_environment(value)

    def test_api_documentation_is_disabled_only_in_production(self):
        self.assertEqual(
            api_documentation_paths("production"),
            {"docs_url": None, "redoc_url": None, "openapi_url": None},
        )
        self.assertEqual(
            api_documentation_paths("development"),
            {
                "docs_url": "/docs",
                "redoc_url": "/redoc",
                "openapi_url": "/openapi.json",
            },
        )

    def test_secret_key_rejects_missing_placeholder_and_weak_values(self):
        for value in (None, "", "change-me", "short-secret"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    validate_secret_key(value)

    def test_secret_key_warns_before_recommended_rotation_length(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = validate_secret_key("valid-but-needs-rotation")

        self.assertEqual(result, "valid-but-needs-rotation")
        self.assertEqual(len(caught), 1)
        self.assertIn("rotated", str(caught[0].message))

    def test_secret_key_accepts_long_random_value_without_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            result = validate_secret_key("a-secure-random-value-with-32-characters")

        self.assertEqual(result, "a-secure-random-value-with-32-characters")
        self.assertEqual(caught, [])

    def test_cors_origins_are_validated_normalized_and_deduplicated(self):
        origins = parse_cors_origins(
            "http://localhost:5173/, https://example.com, http://localhost:5173"
        )

        self.assertEqual(origins, ["http://localhost:5173", "https://example.com"])

        for value in ("", "*", "localhost:5173", "https://example.com/path"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    parse_cors_origins(value)

    def test_admin_user_ids_are_explicit_normalized_and_validated(self):
        self.assertEqual(parse_admin_user_ids(None), set())
        self.assertEqual(
            parse_admin_user_ids(" 7,12,7 "),
            {7, 12},
        )
        for value in ("not-a-number", "0", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    parse_admin_user_ids(value)

    def test_boolean_settings_are_explicit(self):
        for value in ("true", "1", "YES", "on"):
            self.assertTrue(parse_boolean_setting("FORCE_HTTPS", value))
        for value in ("false", "0", "NO", "off"):
            self.assertFalse(parse_boolean_setting("FORCE_HTTPS", value))
        self.assertFalse(parse_boolean_setting("FORCE_HTTPS", None))
        with self.assertRaises(RuntimeError):
            parse_boolean_setting("FORCE_HTTPS", "sometimes")

    def test_trusted_hosts_are_normalized_and_reject_unsafe_values(self):
        self.assertEqual(
            parse_trusted_hosts("Example.COM, api.example.com, example.com"),
            ["example.com", "api.example.com"],
        )
        for value in ("", "*", "https://example.com", "example.com/path", ".example.com"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    parse_trusted_hosts(value)

    def test_production_environment_fails_closed_until_launch_settings_are_safe(self):
        secure = {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql+psycopg://database/habitard?sslmode=require",
            "SECRET_KEY": "a-secure-random-value-with-32-characters",
            "CORS_ORIGINS": "https://habitard.com.do",
            "TRUSTED_HOSTS": "habitard.com.do,api.habitard.com.do",
            "FORCE_HTTPS": "true",
            "ADMIN_USER_IDS": "1",
            "FRONTEND_URL": "https://habitard.com.do",
            "SMTP_HOST": "smtp.provider.test",
            "SMTP_USERNAME": "no-reply@habitard.com.do",
            "SMTP_PASSWORD": "provider-app-password",
            "SMTP_FROM": "HabitaRD <no-reply@habitard.com.do>",
            "SMTP_USE_TLS": "true",
            "SMTP_PORT": "587",
            "SMTP_TIMEOUT_SECONDS": "10",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            "PROPERTY_IMAGE_STORAGE": "s3",
            "OBJECT_STORAGE_BUCKET": "habitard-images",
            "OBJECT_STORAGE_ACCESS_KEY_ID": "storage-access-key",
            "OBJECT_STORAGE_SECRET_ACCESS_KEY": "storage-secret-key",
            "OBJECT_STORAGE_PUBLIC_BASE_URL": "https://images.habitard.com.do",
        }
        validate_production_environment(secure)

        unsafe_cases = (
            {**secure, "FORCE_HTTPS": "false"},
            {**secure, "ADMIN_USER_IDS": ""},
            {**secure, "FRONTEND_URL": "http://habitard.com.do"},
            {**secure, "CORS_ORIGINS": "http://habitard.com.do"},
            {**secure, "TRUSTED_HOSTS": "localhost"},
            {**secure, "DATABASE_URL": "sqlite:///habitard.db"},
            {**secure, "DATABASE_URL": "postgresql://database/habitard?sslmode=require"},
            {**secure, "DATABASE_URL": "postgresql+psycopg://database/habitard"},
            {**secure, "DATABASE_URL": "postgresql+psycopg://database/habitard?sslmode=disable"},
            {**secure, "SMTP_FROM": "no-reply@example.com"},
            {**secure, "SMTP_USERNAME": ""},
            {**secure, "SMTP_PASSWORD": ""},
            {**secure, "SMTP_USE_TLS": "false"},
            {**secure, "SMTP_PORT": "70000"},
            {**secure, "SMTP_TIMEOUT_SECONDS": "0"},
            {**secure, "ACCESS_TOKEN_EXPIRE_MINUTES": "61"},
            {**secure, "SMTP_FROM": "not-an-address"},
            {**secure, "SMTP_FROM": "HabitaRD <no-reply@habitard.com.do>\nBcc: attacker@example.net"},
        )
        for settings in unsafe_cases:
            with self.subTest(settings=settings):
                with self.assertRaises(RuntimeError):
                    validate_production_environment(settings)

        validate_production_environment({"APP_ENV": "development"})
        with self.assertRaises(RuntimeError):
            validate_production_environment({"APP_ENV": "prodution"})


if __name__ == "__main__":
    unittest.main()
