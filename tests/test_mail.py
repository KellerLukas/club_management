from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import requests
from O365 import Account
from O365.message import Message

from club_management.mail import forward_email, get_attachments, send_email


class TestMail(TestCase):
    def setUp(self) -> None:
        self.enterContext(
            patch.object(
                requests.Session,
                "request",
                side_effect=AssertionError("Tests must not contact live services."),
            )
        )

    def test_file_attachments_are_downloaded_once(self) -> None:
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
        self.assertEqual(get_attachments(message), [file])
        self.assertEqual(get_attachments(message), [file])
        collection.download_attachments.assert_called_once()

    def test_sending_uses_plain_text_and_bcc(self) -> None:
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
        self.assertEqual(payload["body"], {"contentType": "text", "content": "Ready"})
        self.assertEqual(
            payload["bccRecipients"],
            [{"emailAddress": {"address": "member@example.com"}}],
        )

    def test_forwarding_preserves_the_original_body(self) -> None:
        message = Mock()
        forwarded = message.forward.return_value
        forwarded.body = "<p>Original</p>"
        forward_email(
            message, recipients=["member@example.com"], additional_body="<p>Note</p>"
        )
        self.assertEqual(forwarded.body, "<p>Note</p><p>Original</p>")
        forwarded.to.add.assert_called_once_with("member@example.com")
        forwarded.send.assert_called_once()
