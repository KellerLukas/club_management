from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from O365.mailbox import MailBox
from O365.message import Message, MessageAttachment


def get_inbox_messages(
    mailbox: MailBox, *, unread_only: bool = True, limit: int = 100
) -> list[Message]:
    """Fetch inbox messages without changing read status or downloading attachments.

    Returns native O365 messages and follows pagination up to the positive limit.
    Set unread_only=False to include messages that were already read.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer.")
    return list(
        mailbox.inbox_folder().get_messages(
            limit=limit,
            query="isRead eq false" if unread_only else None,
            download_attachments=False,
        )
    )


def get_message(mailbox: MailBox, message_id: str) -> Message:
    """Fetch by O365 object_id without marking read or downloading attachments."""
    if not message_id.strip():
        raise ValueError("message_id is required.")
    message: Message | None = mailbox.get_message(
        object_id=message_id, download_attachments=False
    )
    if message is None:
        raise RuntimeError("Could not retrieve the message.")
    return message


def mark_as_read(message: Message) -> None:
    """Update only read status and raise if O365 reports a failed update."""
    if not message.mark_as_read():
        raise RuntimeError("Could not mark the message as read.")


def get_attachments(message: Message) -> list[MessageAttachment]:
    """Download file attachments once, excluding inline content."""
    if not message.has_attachments:
        return []
    if not message.attachments and not message.attachments.download_attachments():
        raise RuntimeError("Could not download message attachments.")
    return [
        attachment
        for attachment in message.attachments
        if attachment.attachment_type == "file" and not attachment.is_inline
    ]


def send_email(
    mailbox: MailBox,
    *,
    subject: str,
    body: str,
    recipients: Sequence[str] = (),
    cc: Sequence[str] = (),
    bcc: Sequence[str] = (),
    reply_to: Sequence[str] = (),
    attachments: Sequence[Path] = (),
    body_type: Literal["text", "html"] = "text",
) -> None:
    message = mailbox.new_message()
    message.subject = subject
    message.body_type = body_type
    message.body = body
    for target, addresses in (
        (message.to, recipients),
        (message.cc, cc),
        (message.bcc, bcc),
        (message.reply_to, reply_to),
    ):
        for address in addresses:
            target.add(address)
    for path in attachments:
        message.attachments.add(str(path))
    if not message.send():
        raise RuntimeError("Could not send the message.")


def forward_email(
    message: Message,
    *,
    recipients: Sequence[str],
    subject: str | None = None,
    additional_body: str = "",
) -> None:
    """Forward a message with an optional subject and body prefix."""
    forwarded = message.forward()
    if forwarded is None:
        raise RuntimeError("Could not prepare the forwarded message.")
    if subject is not None:
        forwarded.subject = subject
    if additional_body:
        forwarded.body = additional_body + forwarded.body
    for address in recipients:
        forwarded.to.add(address)
    if not forwarded.send():
        raise RuntimeError("Could not forward the message.")
