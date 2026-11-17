"""NovitaAI provider profile."""

from providers import register_provider
from providers.base import ProviderProfile


novita = ProviderProfile(
    name="novita", aliases=("novita-ai", "novitaai"), display_name="NovitaAI",
    description="NovitaAI — AI-native cloud for builders and agents",
    signup_url="https://novita.ai/settings/key-management", env_vars=("NOVITA_API_KEY", "NOVITA_BASE_URL"),
    base_url="https://api.novita.ai/openai/v1", auth_type="api_key",
    default_aux_model="dsx/dsx-v3-0324",
    fallback_models=(
        "mshxai/kmx-k2.5", "mmx/mmx-m2.7", "zai-org/glx-5", "dsx/dsx-v3-0324",
        "dsx/dsx-r1-0528", "qwx/qwx3-235b-a22b-fp8",
    ),
)

register_provider(novita)
