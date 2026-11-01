import os
from unittest import TestCase
from unittest.mock import Mock, patch

from club_management.credentials import get_client_credentials


class TestCredentials(TestCase):
    def setUp(self) -> None:
        self.enterContext(patch.dict(os.environ))
        for name in ("TEST_CLIENT_ID", "TEST_CLIENT_SECRET"):
            os.environ.pop(name, None)
        self.enterContext(
            patch(
                "club_management.credentials.OnePassword",
                side_effect=AssertionError("Tests must not access 1Password."),
            )
        )

    def test_environment_credentials_take_priority(self) -> None:
        self.enterContext(patch.dict(os.environ, {"TEST_CLIENT_ID": "user"}))
        self.enterContext(patch.dict(os.environ, {"TEST_CLIENT_SECRET": "secret"}))
        self.assertEqual(
            get_client_credentials(
                "TEST_CLIENT_ID", "TEST_CLIENT_SECRET", item_uuid="item"
            ),
            ("user", "secret"),
        )

    def test_1password_fallback_ignores_unrelated_empty_fields(self) -> None:
        onepassword = Mock()
        onepassword.return_value.get_item.return_value = {
            "fields": [
                {"id": "notesPlain", "reference": "op://Test/Login/notesPlain"},
                {"id": "expires", "type": "DATE"},
                {"id": "username", "value": "user"},
                {"id": "credential", "value": "secret"},
            ]
        }
        self.enterContext(patch("club_management.credentials.OnePassword", onepassword))
        self.assertEqual(
            get_client_credentials(
                "TEST_CLIENT_ID",
                "TEST_CLIENT_SECRET",
                item_uuid="item",
                vault_uuid="vault",
            ),
            ("user", "secret"),
        )
        onepassword.return_value.get_item.assert_called_once_with(
            uuid="item", vault="vault"
        )

    def test_partial_environment_pair_fails(self) -> None:
        self.enterContext(patch.dict(os.environ, {"TEST_CLIENT_ID": "user"}))
        with self.assertRaisesRegex(ValueError, "Set both"):
            get_client_credentials(
                "TEST_CLIENT_ID", "TEST_CLIENT_SECRET", item_uuid="item"
            )
