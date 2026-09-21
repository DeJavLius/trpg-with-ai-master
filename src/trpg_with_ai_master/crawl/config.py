from dataclasses import dataclass
from typing import Any

from trpg_with_ai_master.config import Config, require_bool_env, require_env


@dataclass(frozen=True, kw_only=True)
class CrawlConfig(Config):
    site_url: str
    url_keyword: str
    user_agent: str
    do_crawl: bool
    do_create: bool

    @classmethod
    def _extra_kwargs(cls) -> dict[str, str | bool]:
        return {
            "site_url": require_env("DW_SITE").rstrip("/"),
            "url_keyword": require_env("URL_KEYWORD"),
            "user_agent": require_env("USER_AGENT"),
            "do_crawl": require_bool_env("DO_CRAWL"),
            "do_create": require_bool_env("DO_CREATE"),
        }
