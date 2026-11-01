from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from O365.mailbox import MailBox
from O365.message import Message, MessageAttachment


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
