import unittest

from datetime import (
    date,
    timedelta,
)

from types import SimpleNamespace

from unittest.mock import (
    ANY,
    patch,
)

from fastapi import HTTPException

from pydantic import ValidationError

from backend.models import (
    UserCreate,
    UserUpdate,
)

from backend.services.user_service import (
    change_password,
    get_public_profile,
    update_current_user,
)


class ProfileModelTests(
    unittest.TestCase
):
    def test_structured_registration_builds_display_name(
        self
    ):
        user = UserCreate(
            first_name=" Ana ",
            middle_name=" María ",
            last_name=" Pérez ",
            date_of_birth="1994-06-15",
            bio=(
                "  I help families "
                "find a home.  "
            ),
            email="ANA@EXAMPLE.COM",
            password="password123",
        )

        self.assertEqual(
            user.name,
            "Ana María Pérez",
        )

        self.assertEqual(
            user.email,
            "ana@example.com",
        )

        self.assertEqual(
            user.bio,
            (
                "I help families "
                "find a home."
            ),
        )


    def test_structured_profile_requires_last_name_and_birth_date(
        self
    ):
        with self.assertRaises(
            ValidationError
        ):
            UserUpdate(
                first_name="Ana",
                email="ana@example.com",
            )


    def test_birth_date_cannot_be_in_the_future(
        self
    ):
        with self.assertRaises(
            ValidationError
        ):
            UserCreate(
                first_name="Ana",

                last_name="Pérez",

                date_of_birth=
                    date.today()
                    + timedelta(days=2),

                email=
                    "ana@example.com",

                password=
                    "password123",
            )


    def test_registration_rejects_unknown_fields(
        self
    ):
        with self.assertRaises(
            ValidationError
        ):
            UserCreate(
                name="Seller",
                email="seller@example.com",
                password="password123",

                # This was the exact
                # frontend bug.
                role="seller",
            )


    def test_profile_update_rejects_unknown_fields(
        self
    ):
        with self.assertRaises(
            ValidationError
        ):
            UserUpdate(
                name="Ana Perez",

                email=
                    "ana@example.com",

                unexpected_field=
                    "should fail",
            )


    def test_public_profile_returns_only_explicitly_shared_fields(
        self
    ):
        user = SimpleNamespace(
            id=12,

            name=
                "Ana María Pérez",

            first_name=
                "Ana",

            email=
                "private@example.com",

            date_of_birth=
                date(
                    1994,
                    6,
                    15,
                ),

            bio=
                "Shared biography",

            public_profile_enabled=
                True,

            public_name_mode=
                "first_name",

            public_bio_visible=
                False,

            public_display_name=
                "Ana",
        )

        with patch(
            (
                "backend.services.user_service."
                "user_repository.get_user_by_id"
            ),
            return_value=user,
        ):
            profile = (
                get_public_profile(
                    object(),
                    user.id,
                )
            )

        self.assertEqual(
            profile,
            {
                "id": 12,
                "display_name": "Ana",
                "bio": None,
            },
        )

        self.assertNotIn(
            "email",
            profile,
        )

        self.assertNotIn(
            "date_of_birth",
            profile,
        )


    def test_private_profile_is_not_discoverable(
        self
    ):
        user = SimpleNamespace(
            public_profile_enabled=False
        )

        with patch(
            (
                "backend.services.user_service."
                "user_repository.get_user_by_id"
            ),
            return_value=user,
        ):
            with self.assertRaises(
                HTTPException
            ) as raised:
                get_public_profile(
                    object(),
                    12,
                )

        self.assertEqual(
            raised.exception.status_code,
            404,
        )


    def test_social_account_can_create_its_first_password(
        self
    ):
        user = SimpleNamespace(
            id=12,
            has_password=False,
            password="unused",
            token_generation=1,
        )

        with (
            patch(
                (
                    "backend.services.user_service."
                    "user_repository.get_user_by_id"
                ),
                return_value=user,
            ),

            patch(
                (
                    "backend.services.user_service."
                    "user_repository.update_user"
                )
            ),
        ):
            result = change_password(
                object(),
                user.id,
                None,
                "new-password-123",
            )

        self.assertTrue(
            user.has_password
        )

        self.assertEqual(
            user.token_generation,
            2,
        )

        self.assertEqual(
            result["message"],
            (
                "Password created "
                "successfully"
            ),
        )


    def test_password_account_still_requires_current_password(
        self
    ):
        user = SimpleNamespace(
            id=12,
            has_password=True,
            password="stored",
            token_generation=1,
        )

        with patch(
            (
                "backend.services.user_service."
                "user_repository.get_user_by_id"
            ),
            return_value=user,
        ):
            with self.assertRaises(
                HTTPException
            ) as raised:
                change_password(
                    object(),
                    user.id,
                    None,
                    "new-password-123",
                )

        self.assertEqual(
            raised.exception.status_code,
            400,
        )


    def test_seller_cannot_change_phone_without_verifying_new_number(
        self
    ):
        user = SimpleNamespace(
            id=12,

            account_type=
                "seller",

            name=
                "Ana Perez",

            first_name=
                "Ana",

            middle_name=
                "",

            last_name=
                "Perez",

            date_of_birth=
                date(1990, 1, 1),

            bio="",

            public_profile_enabled=
                False,

            public_name_mode=
                "first_name",

            public_bio_visible=
                False,

            email=
                "ana@example.com",

            email_verified=
                True,

            password=
                "stored",

            seller_category=
                "owner",

            seller_phone=
                "+18095550123",

            business_name=
                "",

            token_generation=
                1,
        )


        with (
            patch(
                (
                    "backend.services.user_service."
                    "user_repository.get_user_by_id"
                ),
                return_value=user,
            ),

            patch(
                (
                    "backend.services.user_service."
                    "user_repository.get_user_by_email"
                ),
                return_value=user,
            ),
        ):
            with self.assertRaises(
                HTTPException
            ) as raised:
                update_current_user(
                    db=object(),

                    user_id=
                        user.id,

                    name=
                        user.name,

                    email=
                        user.email,

                    seller_category=
                        "owner",

                    seller_phone=
                        "+18295550123",
                )


        self.assertEqual(
            raised.exception.status_code,
            422,
        )


    def test_verified_seller_phone_change_consumes_proof(
        self
    ):
        user = SimpleNamespace(
            id=12,

            account_type=
                "seller",

            name=
                "Ana Perez",

            first_name=
                "Ana",

            middle_name=
                "",

            last_name=
                "Perez",

            date_of_birth=
                date(1990, 1, 1),

            bio="",

            public_profile_enabled=
                False,

            public_name_mode=
                "first_name",

            public_bio_visible=
                False,

            email=
                "ana@example.com",

            email_verified=
                True,

            password=
                "stored",

            seller_category=
                "owner",

            seller_phone=
                "+18095550123",

            business_name=
                "",

            token_generation=
                1,
        )


        with (
            patch(
                (
                    "backend.services.user_service."
                    "user_repository.get_user_by_id"
                ),
                return_value=user,
            ),

            patch(
                (
                    "backend.services.user_service."
                    "user_repository.get_user_by_email"
                ),
                return_value=user,
            ),

            patch(
                (
                    "backend.services.user_service."
                    "consume_seller_phone_verification"
                )
            ) as consume_proof,

            patch(
                (
                    "backend.services.user_service."
                    "user_repository.update_user"
                ),
                side_effect=lambda _db, value: value,
            ),
        ):
            updated, email_changed = (
                update_current_user(
                    db=object(),

                    user_id=
                        user.id,

                    name=
                        user.name,

                    email=
                        user.email,

                    seller_category=
                        "agent",

                    seller_phone=
                        "+18295550123",

                    business_name=
                        "Nueva Agencia",

                    seller_phone_verification_token=
                        "v" * 32,
                )
            )


        consume_proof.assert_called_once_with(
            ANY,
            "v" * 32,
            "+18295550123",
        )

        self.assertFalse(
            email_changed
        )

        self.assertEqual(
            updated.seller_phone,
            "+18295550123",
        )

        self.assertEqual(
            updated.seller_category,
            "agent",
        )


if __name__ == "__main__":
    unittest.main()