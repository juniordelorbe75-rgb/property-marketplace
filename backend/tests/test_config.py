import unittest
import warnings

from backend.config import parse_cors_origins, validate_secret_key


class ConfigurationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
