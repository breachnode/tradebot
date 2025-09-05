from typing import Any, Dict, Optional
import time
import requests


class HttpClient:
    def __init__(self, base_url: str, bearer_token: str, timeout_seconds: int = 15):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
                # Do not set Content-Type globally; only for POST form requests
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        merged_headers = {}
        if headers:
            merged_headers.update(headers)

        for attempt in range(retries + 1):
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=merged_headers or None,
                timeout=self.timeout_seconds,
            )

            # Retry on 429 and 5xx
            if response.status_code in (429,) or 500 <= response.status_code < 600:
                if attempt < retries:
                    time.sleep(backoff_seconds * (2 ** attempt))
                    continue
            return response

        return response

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post_form(
        self, path: str, *, data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return self._request("POST", path, data=data, headers=headers)

    def delete(self, path: str) -> requests.Response:
        return self._request("DELETE", path)

