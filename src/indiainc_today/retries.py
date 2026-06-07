"""Retry decorator configuration for robust HTTP requests.

Uses tenacity to retry transient network/server failures.
"""

import logging
import re
from typing import Any
from tenacity import (
    retry,
    wait_random_exponential,
    stop_after_attempt,
    retry_if_exception,
    before_sleep_log,
)
from . import config

logger = logging.getLogger(__name__)

# Status codes to retry
RETRY_STATUS_CODES = {408, 429, 502, 503, 504}


def should_retry_exception(exception: Exception) -> bool:
    """Predicate to determine if an exception should trigger a retry.

    Retries on:
    - TimeoutError (client-side timeout)
    - ConnectionError/HTTPError if status code matches RETRY_STATUS_CODES.

    Args:
        exception: The exception raised during request.

    Returns:
        True if the exception should be retried, False otherwise.
    """
    if isinstance(exception, TimeoutError):
        return True

    # Check exception messages for status codes
    msg = str(exception)
    for code in RETRY_STATUS_CODES:
        if re.search(rf"\b{code}\b", msg):
            return True

    return False


def get_retry_decorator() -> Any:
    """Returns a configured tenacity retry decorator.

    Returns:
        A tenacity retry decorator.
    """
    return retry(
        stop=stop_after_attempt(config.TOTAL_RETRIES),
        wait=wait_random_exponential(
            multiplier=config.RETRY_MULTIPLIER,
            min=config.RETRY_MIN_DELAY,
            max=config.RETRY_MAX_DELAY,
        ),
        retry=retry_if_exception(should_retry_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )


# Export a ready-to-use decorator
retry_exchange = get_retry_decorator()
