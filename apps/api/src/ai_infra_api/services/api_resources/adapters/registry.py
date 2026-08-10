from ai_infra_api.services.api_resources.adapters.base import ProviderAdapter
from ai_infra_api.services.api_resources.adapters.generic_openai import (
    GenericOpenAIAdapter,
    OpenAIAdapter,
)

ADAPTERS: dict[str, ProviderAdapter] = {
    adapter.slug: adapter for adapter in (OpenAIAdapter(), GenericOpenAIAdapter())
}


def get_adapter(slug: str) -> ProviderAdapter:
    try:
        return ADAPTERS[slug]
    except KeyError as error:
        raise ValueError("unsupported API provider") from error
