from pathlib import Path
from typing import Literal, cast

from O365.drive import File, Folder


def upload_file(
    folder: Folder,
    file_path: Path,
    *,
    filename: str | None = None,
    conflict_handling: Literal["fail", "replace", "rename"] = "fail",
) -> File:
    """Upload a file using the requested conflict policy, failing by default."""
    if file_path.stat().st_size == 0:
        raise ValueError("The uploaded file must not be empty.")
    uploaded = folder.upload_file(
        file_path,
        item_name=filename,
        upload_in_chunks=True,
        conflict_handling=conflict_handling,
    )
    if uploaded is None:
        raise RuntimeError("Could not upload the file.")
    return cast(File, uploaded)
