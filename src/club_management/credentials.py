import os

from onepassword import OnePassword  # type: ignore[import-untyped]


def get_client_credentials(
    client_id_env_var: str,
    client_secret_env_var: str,
    *,
    item_uuid: str | None = None,
    vault_uuid: str | None = None,
    client_id_field: str = "username",
    client_secret_field: str = "credential",
) -> tuple[str, str]:
    """Read an environment pair, falling back to 1Password when both are absent."""
    client_id = os.getenv(client_id_env_var)
    client_secret = os.getenv(client_secret_env_var)
    if client_id is not None or client_secret is not None:
        if not client_id or not client_secret:
            raise ValueError(
                f"Set both '{client_id_env_var}' and '{client_secret_env_var}'."
            )
        return client_id, client_secret
    if item_uuid is None:
        raise ValueError("Environment credentials or a 1Password item are required.")
    item = OnePassword().get_item(uuid=item_uuid, vault=vault_uuid)
    fields = {field["id"]: field["value"] for field in item["fields"]}
    return fields[client_id_field], fields[client_secret_field]
