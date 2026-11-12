import os
import time

import requests
from dotenv import load_dotenv
from tavily import (
    BadRequestError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
    TavilyClient,
    UsageLimitExceededError,
)
from tavily.errors import ForbiddenError


load_dotenv()

_MAX_CONTEXT_FOR_SEARCH = 500
_MAX_RESULTS = 3
_SEARCH_TIMEOUT_SECONDS = 15


class ResearchError(RuntimeError):
    """Raised when a usable Tavily research response is unavailable."""


def _is_temporary_search_error(error):
    status = getattr(error, "status_code", None)
    if status is None:
        response = getattr(error, "response", None)
        status = getattr(response, "status_code", None)

    return (
        isinstance(error, (requests.exceptions.ConnectionError,
                           requests.exceptions.Timeout, TimeoutError))
        or status == 429
        or (status is not None and 500 <= status < 600)
    )


def research_company(company, meeting_context=""):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ResearchError("Tavily API key is missing. Set TAVILY_API_KEY in .env.")

    company = company.strip()
    context = meeting_context.strip()
    query = (
        f"{company}: {context[:_MAX_CONTEXT_FOR_SEARCH]}. "
        "Recent news, business developments, opportunities, and risks."
    )
    client = TavilyClient(api_key=api_key)

    for attempt in range(2):
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=_MAX_RESULTS,
                include_answer=True,
                timeout=_SEARCH_TIMEOUT_SECONDS,
            )
            if not response.get("results") and not response.get("answer"):
                raise ResearchError(
                    "Tavily returned no research sources. Try a more specific "
                    "company name or meeting context."
                )
            return response
        except ResearchError:
            raise
        except (
            requests.exceptions.RequestException,
            TimeoutError,
            BadRequestError,
            InvalidAPIKeyError,
            MissingAPIKeyError,
            UsageLimitExceededError,
            ForbiddenError,
        ) as error:
            if attempt == 0 and _is_temporary_search_error(error):
                time.sleep(1)
                continue

            status = getattr(error, "status_code", None)
            if status is None:
                response_obj = getattr(error, "response", None)
                status = getattr(response_obj, "status_code", None)
            if isinstance(error, (InvalidAPIKeyError, MissingAPIKeyError)):
                message = "Tavily rejected the API key. Check TAVILY_API_KEY in .env."
            elif (
                isinstance(error, UsageLimitExceededError)
                or status == 429
            ):
                message = "Tavily's usage limit was reached. Check the Tavily account quota."
            elif isinstance(error, ForbiddenError) or status in (401, 403):
                message = "Tavily rejected the API key or request permissions. Check the account configuration."
            elif _is_temporary_search_error(error):
                if status is not None:
                    message = (
                        f"Tavily remained unavailable (HTTP {status}) after a retry. "
                        "Check Tavily service status and try again."
                    )
                else:
                    message = (
                        "Tavily could not be reached after a retry. Check the network "
                        "connection and try again."
                    )
            else:
                message = (
                    f"Tavily research failed (HTTP {status}). Check the Tavily "
                    "configuration and try again."
                    if status is not None
                    else "Tavily research failed. Check the Tavily configuration and try again."
                )
            raise ResearchError(message) from error
