# Club management

Small shared Python helpers for credentials, Microsoft 365 operations, filenames,
and application logging. Requires Python 3.11 or newer.

## Install and develop

After publication, install with `uv add "club-management==0.1.0"`.
For package development:

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
```

Builds are written to `dist/`; publish a reviewed release manually with
`uv publish`. The licence is MIT and the check workflow does not publish.

## Credentials

```python
from club_management.credentials import get_client_credentials

credentials = get_client_credentials(
    "MICROSOFT_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET",
    item_uuid="item-id",
)
```

The result is a `(client_id, client_secret)` tuple. A complete nonempty
process-environment pair takes priority. When both variables are absent, the
`1password` package reads the item using the signed-in `op` CLI. A partial or
empty environment pair raises an error. The Pi therefore needs no CLI when
both variables are set; the Mac can leave them absent to use 1Password.
Environment files are not loaded automatically.

Optional arguments select a vault and the item field IDs; defaults are
`username` and `credential`. Applications supply their own identifiers and secrets.

## Microsoft 365

Use `O365.Account` directly for application or delegated authentication,
mailbox queries, read status, folder discovery, and downloads. For example:

```python
from pathlib import Path

from O365 import Account
from O365.utils.token import MemoryTokenBackend

from club_management.mail import get_attachments, send_email
from club_management.sharepoint import upload_file

account = Account(
    credentials,
    tenant_id="tenant-id",
    auth_flow_type="credentials",
    token_backend=MemoryTokenBackend(),
    timeout=30,
    request_retries=0,
    raise_http_errors=True,
)
if not account.authenticate():
    raise RuntimeError("Microsoft authentication failed.")

mailbox = account.mailbox(resource="automation@example.com")
for message in mailbox.inbox_folder().get_messages(query="isRead eq false", limit=100):
    attachments = get_attachments(message)
    # Process the message, then acknowledge success explicitly.
    message.mark_as_read()

site = account.sharepoint().get_site("site-id")
folder = site.get_default_document_library().get_item_by_path("/Exports")
uploaded = upload_file(folder, Path("report.xlsx"))
folder_url = folder.web_url

send_email(
    mailbox, subject="Export ready", body=uploaded.web_url, bcc=["member@example.com"]
)
```

`get_attachments` returns native O365 file attachments, excludes inline content,
and reuses already downloaded attachments. Their `content` is base64 encoded;
message-specific parsing belongs to the application. `forward_email` accepts a
native message and optional subject and body prefix, preserving its body format.
`send_email` defaults to plain text and accepts separate recipient groups,
reply addresses, and local attachment paths.

`upload_file` uses O365 upload sessions so its conflict policy applies to small
files too: `fail` by default, with `replace` and `rename` available explicitly.
Empty files are rejected. Use O365 objects directly for other file operations.
Microsoft permissions and token-file storage are configured by each application.

## Logging and filenames

```python
from club_management.filenames import sanitize_filename
from club_management.logging_config import setup_logging

setup_logging(log_file=Path("logs/application.log"))
filename = sanitize_filename("Member list: November.xlsx")
```

Logging uses standard Python handlers, UTC timestamps, console output, and an
optional file rotating at 5 MB with five backups. Setup replaces only its own
handlers; imports do not configure logging. Keep log files private or collect
console logs through the service manager, with one rotation owner per file.
O365 and MSAL default to WARNING; logs are not automatically redacted.
Filename cleanup preserves Unicode and rejects names over 240 UTF-8 bytes.
