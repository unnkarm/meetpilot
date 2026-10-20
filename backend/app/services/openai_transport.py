"""Server-only OpenAI HTTP transport; errors never include keys or prompt bodies."""

import httpx

from app.core.config import settings


class OpenAIRequestError(RuntimeError):
    pass


def post_openai(path: str, payload: dict, *, timeout: float) -> dict:
    key = settings.OPENAI_API_KEY.get_secret_value().strip()
    if not key:
        raise OpenAIRequestError("OPENAI_API_KEY must be configured on the server")
    try:
        # A fixed origin and disabled redirects prevent credentials being routed
        # to a user-supplied endpoint. No API requests occur at import/startup.
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.post(
                "https://api.openai.com/v1/" + path,
                headers={"Authorization": "Bearer " + key},
                json=payload,
            )
            if not 200 <= response.status_code < 300:
                raise OpenAIRequestError(f"OpenAI request failed (HTTP {response.status_code})")
            result = response.json()
    except httpx.HTTPError:
        raise OpenAIRequestError("OpenAI connection failed or timed out") from None
    except ValueError:
        raise OpenAIRequestError("OpenAI returned invalid JSON") from None
    if not isinstance(result, dict):
        raise OpenAIRequestError("OpenAI returned an invalid response object")
    return result
