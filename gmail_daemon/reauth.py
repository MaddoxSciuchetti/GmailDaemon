from __future__ import annotations

from .auth import SCOPES, get_credentials
from .config import load_config


def main() -> None:
    config = load_config()
    get_credentials(config, force_reauth=True)
    print("Google OAuth token refreshed with scopes:")
    for scope in SCOPES:
        print(f"- {scope}")


if __name__ == "__main__":
    main()
