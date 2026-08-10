from ai_infra_api.db.models import ApiProvider
from ai_infra_api.services.api_resources.adapters.base import ProviderAdapter
from ai_infra_api.services.api_resources.adapters.generic_openai import (
    AliyunBailianAdapter,
    AnthropicAdapter,
    ClaudeCodeAdapter,
    CodexAdapter,
    ConfiguredOpenAIAdapter,
    GenericOpenAIAdapter,
    OpenAIAdapter,
)

ADAPTERS: dict[str, ProviderAdapter] = {
    adapter.slug: adapter
    for adapter in (
        OpenAIAdapter(),
        CodexAdapter(),
        AnthropicAdapter(),
        ClaudeCodeAdapter(),
        AliyunBailianAdapter(),
        GenericOpenAIAdapter(),
    )
}


def get_adapter(slug: str) -> ProviderAdapter:
    try:
        return ADAPTERS[slug]
    except KeyError as error:
        raise ValueError("unsupported API provider") from error


def get_adapter_for_provider(provider: ApiProvider) -> ProviderAdapter:
    if provider.provider_type == "custom":
        if provider.adapter_kind == "anthropic":
            return AnthropicAdapter()
        return ConfiguredOpenAIAdapter(provider.slug, provider.display_name)
    return get_adapter(provider.slug)
