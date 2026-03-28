"""WorkOS client for authentication and user management.

Wraps the WorkOS Python SDK for AuthKit-based login.
Initialized lazily — returns None if WORKOS_API_KEY or WORKOS_CLIENT_ID are not set,
allowing AUTH_BYPASS mode to work without WorkOS credentials.
"""

import logging
from typing import Optional

from workos import WorkOSClient as _WorkOSClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkOSClient:
    """Thin wrapper around the WorkOS SDK for auth operations."""

    def __init__(self, api_key: str, client_id: str, redirect_uri: str) -> None:
        self._client = _WorkOSClient(api_key=api_key, client_id=client_id)
        self._redirect_uri = redirect_uri

    def get_authorization_url(self) -> str:
        """Generate a WorkOS AuthKit authorization URL.

        Returns:
            The authorization URL to redirect the user to.
        """
        return self._client.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=self._redirect_uri,
        )

    def authenticate_with_code(self, code: str) -> dict:
        """Exchange an authorization code for user credentials.

        Args:
            code: The authorization code from the OAuth callback.

        Returns:
            A dict with keys: id, email, first_name, last_name.
        """
        auth_response = self._client.user_management.authenticate_with_code(
            code=code,
        )
        user = auth_response.user
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    def get_user_profile(self, user_id: str) -> dict:
        """Retrieve a user profile by WorkOS user ID.

        Args:
            user_id: The WorkOS user ID.

        Returns:
            A dict with keys: id, email, first_name, last_name.
        """
        user = self._client.user_management.get_user(user_id=user_id)
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }


def _init_workos_client() -> Optional[WorkOSClient]:
    """Initialize the WorkOS client if credentials are configured."""
    if settings.WORKOS_API_KEY and settings.WORKOS_CLIENT_ID:
        logger.info("WorkOS client initialized")
        return WorkOSClient(
            api_key=settings.WORKOS_API_KEY,
            client_id=settings.WORKOS_CLIENT_ID,
            redirect_uri=settings.WORKOS_REDIRECT_URI,
        )
    logger.info("WorkOS credentials not set — auth bypass mode only")
    return None


workos_client: Optional[WorkOSClient] = _init_workos_client()
