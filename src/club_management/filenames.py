import re
import unicodedata

MAX_FILENAME_BYTES = 240


def sanitize_filename(filename: str) -> str:
    """Create one filename suitable for SharePoint and local export storage."""
    name = unicodedata.normalize("NFC", filename)
    name = "".join(
        "_"
        if char in '<>:"/\\|?*#%;' or unicodedata.category(char) in {"Cc", "Cs"}
        else char
        for char in name
    )
    name = re.sub(r"_vti_", "-", name, flags=re.IGNORECASE)
    name = name.strip().rstrip(" .") or "unnamed"
    stem = name.split(".", 1)[0].rstrip(" ").upper()
    if (
        stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
        or re.fullmatch(r"(?:COM|LPT)[0-9¹²³]", stem)
        or name.casefold() in {".lock", "desktop.ini", ".ds_store", "forms"}
        or name.startswith("~$")
    ):
        name = "_" + name
    if len(name.encode("utf-8")) > MAX_FILENAME_BYTES:
        raise ValueError(
            f"Filename exceeds {MAX_FILENAME_BYTES} UTF-8 bytes; shorten it."
        )
    return name
