from dotenv import load_dotenv
import os

# Load environment variables from .env (project root / CWD)
load_dotenv()

def require_env(var_name: str) -> str:
    """Fetches a required environment variable, raising a descriptive error if absent.

    Args:
        var_name: Name of the environment variable to retrieve.

    Returns:
        str: The value of the environment variable.

    Raises:
        RuntimeError: If the variable is not set or is an empty string,
            with a hint to check the ``.env`` file or environment configuration.
    """
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(
            f"Environment variable '{var_name}' is not set. "
            "Check your .env file or environment configuration."
        )
    return value
