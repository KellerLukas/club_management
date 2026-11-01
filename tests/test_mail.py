from collections.abc import Iterator
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import requests
from O365 import Account
from O365.mailbox import MailBox
from O365.message import Message

from club_management.mail import (
    forward_email,
    get_attachments,
    get_inbox_messages,
    get_message,
    mark_as_read,
    send_email,
)


class TestMail(TestCase):
    def setUp(self) -> None:
        self.enterContext(
            patch.object(
                requests.Session,
                "request",
                side_effect=AssertionError("Tests must not contact live services."),
            )
        )

    def test_fetching_unread_messages_preserves_read_status(self) -> None:
        mailbox = Mock(spec=MailBox)
        messages = [Mock(spec=Message), Mock(spec=Message)]
        inbox = mailbox.inbox_folder.return_value
        inbox.get_messages.return_value = iter(messages)

        self.assertEqual(get_inbox_messages(mailbox, limit=1000), messages)

        inbox.get_messages.assert_called_once_with(
            limit=1000, query="isRead eq false", download_attachments=False
        )
        for message in messages:
            message.mark_as_read.assert_not_called()
            message.save_message.assert_not_called()

    def test_fetching_can_include_read_messages(self) -> None:
        mailbox = Mock(spec=MailBox)
        inbox = mailbox.inbox_folder.return_value
        inbox.get_messages.return_value = iter(())

        self.assertEqual(get_inbox_messages(mailbox, unread_only=False, limit=10), [])

        inbox.get_messages.assert_called_once_with(
            limit=10, query=None, download_attachments=False
        )

    def test_invalid_limit_does_not_open_inbox(self) -> None:
        mailbox = Mock(spec=MailBox)
        limits: tuple[Any, ...] = (0, -1, True, None, "100")
        for limit in limits:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                get_inbox_messages(mailbox, limit=limit)
        mailbox.inbox_folder.assert_not_called()

    def test_failed_page_does_not_return_partial_results_or_mark_read(self) -> None:
        mailbox = Mock(spec=MailBox)
        message = Mock(spec=Message)

        def pages() -> Iterator[Message]:
            yield message
            raise requests.HTTPError("Could not fetch the next page.")

        mailbox.inbox_folder.return_value.get_messages.return_value = pages()

        with self.assertRaisesRegex(requests.HTTPError, "next page"):
            get_inbox_messages(mailbox)
        message.mark_as_read.assert_not_called()

    def test_getting_a_message_does_not_change_read_status(self) -> None:
        mailbox = Mock(spec=MailBox)
        message = Mock(spec=Message)
        mailbox.get_message.return_value = message

        self.assertIs(get_message(mailbox, "message-id"), message)

        mailbox.get_message.assert_called_once_with(
            object_id="message-id", download_attachments=False
        )
        message.mark_as_read.assert_not_called()
        message.save_message.assert_not_called()

    def test_blank_message_id_does_not_issue_a_lookup(self) -> None:
        mailbox = Mock(spec=MailBox)
        for message_id in ("", " \t"):
            with self.subTest(message_id=message_id), self.assertRaises(ValueError):
                get_message(mailbox, message_id)
        mailbox.get_message.assert_not_called()

    def test_missing_message_is_reported(self) -> None:
        mailbox = Mock(spec=MailBox)
        mailbox.get_message.return_value = None

        with self.assertRaisesRegex(RuntimeError, "Could not retrieve"):
            get_message(mailbox, "missing-id")

    def test_marking_read_does_not_save_other_message_changes(self) -> None:
        message = Mock(spec=Message)
        message.mark_as_read.return_value = True

        mark_as_read(message)

        message.mark_as_read.assert_called_once_with()
        message.save_message.assert_not_called()

    def test_failed_read_status_update_is_reported(self) -> None:
        message = Mock(spec=Message)
        message.mark_as_read.return_value = False

        with self.assertRaisesRegex(RuntimeError, "Could not mark"):
            mark_as_read(message)

    def test_read_status_request_errors_are_preserved(self) -> None:
        message = Mock(spec=Message)
        message.mark_as_read.side_effect = requests.HTTPError("Update failed.")

        with self.assertRaisesRegex(requests.HTTPError, "Update failed"):
            mark_as_read(message)

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
