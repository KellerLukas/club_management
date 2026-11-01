import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import requests
from O365 import Account
from O365.drive import Folder
from O365.message import Message

from club_management.credentials import get_client_credentials
from club_management.filenames import sanitize_filename
from club_management.logging_config import setup_logging
from club_management.mail import forward_email, get_attachments, send_email
from club_management.sharepoint import upload_file


@pytest.fixture(autouse=True)
def isolate_tests(monkeypatch: pytest.MonkeyPatch):
    for name in ("TEST_CLIENT_ID", "TEST_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        requests.Session,
        "request",
        Mock(side_effect=AssertionError("Tests must not contact live services.")),
    )
    monkeypatch.setattr(
        "club_management.credentials.OnePassword",
        Mock(side_effect=AssertionError("Tests must not access 1Password.")),
    )


def test_environment_credentials_take_priority(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEST_CLIENT_ID", "user")
    monkeypatch.setenv("TEST_CLIENT_SECRET", "secret")
    assert get_client_credentials(
        "TEST_CLIENT_ID", "TEST_CLIENT_SECRET", item_uuid="item"
    ) == ("user", "secret")


def test_1password_fallback(monkeypatch: pytest.MonkeyPatch):
    onepassword = Mock()
    onepassword.return_value.get_item.return_value = {
        "fields": [
            {"id": "username", "value": "user"},
            {"id": "credential", "value": "secret"},
        ]
    }
    monkeypatch.setattr("club_management.credentials.OnePassword", onepassword)
    assert get_client_credentials(
        "TEST_CLIENT_ID", "TEST_CLIENT_SECRET", item_uuid="item", vault_uuid="vault"
    ) == ("user", "secret")
    onepassword.return_value.get_item.assert_called_once_with(
        uuid="item", vault="vault"
    )


def test_partial_environment_pair_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEST_CLIENT_ID", "user")
    with pytest.raises(ValueError, match="Set both"):
        get_client_credentials("TEST_CLIENT_ID", "TEST_CLIENT_SECRET", item_uuid="item")


def test_filename_cleanup():
    assert (
        sanitize_filename("Riegen/Übersicht: 2026.xlsx")
        == "Riegen_Übersicht_ 2026.xlsx"
    )
    assert sanitize_filename("CON.xlsx") == "_CON.xlsx"


def test_file_attachments_are_downloaded_once():
    file = Mock(attachment_type="file", is_inline=False)
    source = []
    collection = MagicMock()
    collection.__bool__.side_effect = lambda: bool(source)
    collection.__iter__.side_effect = lambda: iter(source)

    def download():
        source.extend([file, Mock(attachment_type="file", is_inline=True)])
        return True

    collection.download_attachments.side_effect = download
    message = Mock(spec=Message, has_attachments=True, attachments=collection)
    assert get_attachments(message) == [file]
    assert get_attachments(message) == [file]
    collection.download_attachments.assert_called_once()


def test_sending_uses_plain_text_and_bcc():
    account = Account(
        ("client", "secret"), tenant_id="tenant", auth_flow_type="credentials"
    )
    account.con = Mock()
    account.con.post.return_value = Mock(status_code=202)
    send_email(
        account.mailbox(resource="automation@example.com"),
        subject="Report",
        body="Ready",
        bcc=["member@example.com"],
    )
    payload = account.con.post.call_args.kwargs["data"]["message"]
    assert payload["body"] == {"contentType": "text", "content": "Ready"}
    assert payload["bccRecipients"] == [
        {"emailAddress": {"address": "member@example.com"}}
    ]


def test_forwarding_preserves_the_original_body():
    message = Mock()
    forwarded = message.forward.return_value
    forwarded.body = "<p>Original</p>"
    forward_email(
        message, recipients=["member@example.com"], additional_body="<p>Note</p>"
    )
    assert forwarded.body == "<p>Note</p><p>Original</p>"
    forwarded.to.add.assert_called_once_with("member@example.com")
    forwarded.send.assert_called_once()


def test_upload_applies_conflict_policy_to_small_files(tmp_path: Path):
    path = tmp_path / "report.txt"
    path.write_text("Report")
    folder = Mock(spec=Folder)
    assert upload_file(folder, path) is folder.upload_file.return_value
    folder.upload_file.assert_called_once_with(
        path, item_name=None, upload_in_chunks=True, conflict_handling="fail"
    )


def test_repeated_logging_setup_writes_one_record(tmp_path: Path):
    root = logging.getLogger()
    level = root.level
    dependency_levels = {
        name: logging.getLogger(name).level for name in ("O365", "msal")
    }
    path = tmp_path / "application.log"
    try:
        setup_logging(log_file=path)
        setup_logging(log_file=path)
        logging.getLogger("example").info("Übertragung completed")
        content = path.read_text(encoding="utf-8")
        assert content.count("Übertragung completed") == 1
        assert "Z INFO example:" in content
    finally:
        for handler in root.handlers[:]:
            if handler.name == "club_management":
                root.removeHandler(handler)
                handler.close()
        root.setLevel(level)
        for name, logger_level in dependency_levels.items():
            logging.getLogger(name).setLevel(logger_level)
