"""Rate limiting utility for API requests."""

import time


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float = 1.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0

    def wait(self):
        """Wait if necessary to maintain rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
