from dataclasses import dataclass
from typing import Any

from trpg_with_ai_master.config import (
    Config,
    get_env,
    get_int_env,
    require_bool_env,
    require_env,
)


@dataclass(frozen=True, kw_only=True)
class DiagnoseConfig(Config):
    embed_test_model: str | None
    embed_test_max_seq: int | None
    model_compare_repos: list[str]
    model_local_only: bool
    model_index: int
    do_diagnose: bool
    do_compare: bool
    do_model_compare: bool

    @classmethod
    def _extra_kwargs(cls) -> dict[str, Any]:
        return {
            "embed_test_model": get_env("EMBED_TEST_MODEL"),
            "embed_test_max_seq": get_int_env("EMBED_TEST_MAX_SEQ"),
            "model_compare_repos": [
                repo.strip()
                for repo in require_env("MODEL_COMPARE_REPOS").split(",")
                if repo.strip()
            ],
            "model_local_only": require_bool_env("MODEL_LOCAL_ONLY"),
            "model_index": int(require_env("MODEL_INDEX")),
            "do_diagnose": require_bool_env("DO_DIAGNOSE"),
            "do_compare": require_bool_env("DO_COMPARE"),
            "do_model_compare": require_bool_env("DO_MODEL_COMPARE"),
        }
