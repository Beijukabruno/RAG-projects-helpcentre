import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.keycloak_auth import get_keycloak_settings, get_keycloak_authorization_url


def main() -> None:
    settings = get_keycloak_settings()
    print("Keycloak settings:")
    for key, value in settings.items():
        print(f"- {key}: {value}")

    if settings["client_id"] and settings["server_url"] and settings["realm"]:
        print("\nSample authorization URL:")
        print(get_keycloak_authorization_url("http://localhost:3000/callback", state="demo-state"))


if __name__ == "__main__":
    main()
