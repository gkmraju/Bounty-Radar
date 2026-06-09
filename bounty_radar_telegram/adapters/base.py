from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from bounty_radar_telegram.config import Settings
from bounty_radar_telegram.models import Bounty


class BaseAdapter(ABC):
    platform: str = "unknown"

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()

    def get(self, url: str, **kwargs) -> requests.Response:
        timeout = kwargs.pop("timeout", self.settings.request_timeout_seconds)
        response = self.session.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    @abstractmethod
    def fetch(self) -> list[Bounty]:
        raise NotImplementedError
