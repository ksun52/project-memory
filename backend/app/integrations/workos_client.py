"""WorkOS client stub for authentication and user management.

This module will be implemented in Phase 3 with WorkOS SSO/OAuth integration.
All methods currently raise NotImplementedError.
"""


class WorkOSClient:
    """Client for WorkOS authentication operations."""

    def get_authorization_url(self) -> str:
        """Generate a WorkOS authorization URL for SSO login.

        Will redirect users to the WorkOS-hosted login page
        and return them to the app with an authorization code.

        Returns:
            The authorization URL string.
        """
        raise NotImplementedError("WorkOS auth not yet implemented")

    def authenticate_with_code(self, code: str) -> dict:
        """Exchange an authorization code for user credentials.

        Args:
            code: The authorization code from the OAuth callback.

        Returns:
            A dict containing access token and user profile info.
        """
        raise NotImplementedError("WorkOS auth not yet implemented")

    def get_user_profile(self, access_token: str) -> dict:
        """Retrieve the user profile for a given access token.

        Args:
            access_token: A valid WorkOS access token.

        Returns:
            A dict containing user profile fields (id, email, name, etc.).
        """
        raise NotImplementedError("WorkOS auth not yet implemented")


workos_client = WorkOSClient()
