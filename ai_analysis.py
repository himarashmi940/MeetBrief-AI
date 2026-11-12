import json
import os
import time

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


load_dotenv()

_REQUEST_TIMEOUT_SECONDS = 30
_MAX_ATTEMPTS = 2
_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
_MAX_MEETING_CONTEXT_CHARS = 1500
_MAX_RESEARCH_RESULTS = 3
_MAX_RESEARCH_CONTENT_CHARS = 800


class BriefGenerationError(RuntimeError):
    """Raised when Bifrost cannot generate a meeting briefing."""


def _openai_compatible_base_url(configured_url):
    base_url = (configured_url or "http://localhost:8080").rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    if not base_url.endswith("/openai"):
        base_url += "/openai"
    return base_url


def _gateway_error_message(error, model):
    status = error.status_code
    if status in (401, 403):
        return (
            "Bifrost rejected the virtual key. Check BIFROST_API_KEY and the "
            "virtual key's permissions in the Bifrost dashboard."
        )
    if status == 404:
        return (
            f"Bifrost returned 404 for model '{model}'. Confirm that the exact "
            "provider/model name is configured and allowed for this virtual key. "
            "The OpenAI-compatible endpoint should end in /openai."
        )
    if status == 429:
        return (
            "Bifrost or the Gemini provider is rate-limiting requests. Wait briefly "
            "and check the virtual key's rate limits and provider quota."
        )
    if status is not None and status >= 500:
        return (
            f"Bifrost or the Gemini provider returned HTTP {status}. Check provider "
            "availability and the request details in the Bifrost dashboard."
        )
    return (
        f"Bifrost rejected the generation request (HTTP {status}). Check the "
        "configured model and Bifrost request details."
    )


def _compact_research(research_data):
    results = research_data.get("results", []) or []
    compact_results = [
        {
            "title": item.get("title", "")[:200],
            "content": item.get("content", "")[:_MAX_RESEARCH_CONTENT_CHARS],
            "url": item.get("url", "")[:500],
        }
        for item in results[:_MAX_RESEARCH_RESULTS]
    ]
    answer = research_data.get("answer", "")
    return {
        "answer": answer[:_MAX_RESEARCH_CONTENT_CHARS] if answer else "",
        "results": compact_results,
    }


def generate_meeting_brief(company, meeting_context, research_data):
    api_key = os.getenv("BIFROST_API_KEY")
    if not api_key:
        raise BriefGenerationError(
            "Bifrost API key is missing. Set BIFROST_API_KEY in .env."
        )

    model = os.getenv("BIFROST_MODEL_NAME")
    if not model:
        raise BriefGenerationError(
            "Bifrost model name is missing. Set BIFROST_MODEL_NAME to a model "
            "enabled for your virtual key."
        )

    base_url = _openai_compatible_base_url(
        os.getenv("BIFROST_BASE_URL") or "http://localhost:8080"
    )
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=_REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )

    research = _compact_research(research_data)
    prompt = f"""
You are MeetBrief AI, an intelligent meeting preparation assistant.

Prepare a professional meeting briefing using the supplied research.

Company or Person: {company[:200]}
Meeting Context: {meeting_context[:_MAX_MEETING_CONTEXT_CHARS]}

Research:
{json.dumps(research, ensure_ascii=False)}

Create these sections:

1. Company or Person Overview
2. Recent Developments
3. Important Opportunities
4. Potential Risks and Challenges
5. Important Discussion Questions
6. Suggested Meeting Strategy
7. Key Takeaways

Use simple professional language. Distinguish research facts from suggestions.
Do not invent facts; state clearly when the research does not establish something.
"""

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            if not response.choices:
                raise BriefGenerationError(
                    "Bifrost returned no completion choices. Check the model's "
                    "configuration and Bifrost request details."
                )
            result = response.choices[0].message.content
            if not result or not result.strip():
                raise BriefGenerationError(
                    "Gemini returned an empty briefing. Please try again."
                )
            return result.strip()
        except APITimeoutError as error:
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2**attempt)
                continue
            raise BriefGenerationError(
                f"The request to Bifrost at {base_url} timed out after "
                f"{_REQUEST_TIMEOUT_SECONDS} seconds. Check Bifrost's request logs "
                "to see whether the request reached the Gemini provider and how "
                "long it took."
            ) from error
        except APIConnectionError as error:
            raise BriefGenerationError(
                f"Could not connect to Bifrost at {base_url}. Confirm that Bifrost "
                "is running and reachable from the Streamlit process. If Streamlit "
                "runs in a container, localhost refers to that container, not the "
                "host running Bifrost."
            ) from error
        except APIStatusError as error:
            if (
                error.status_code in _RETRYABLE_STATUS_CODES
                and attempt < _MAX_ATTEMPTS - 1
            ):
                time.sleep(2**attempt)
                continue
            raise BriefGenerationError(
                _gateway_error_message(error, model)
            ) from error
