"""Sfxx provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

sfxx = ProviderProfile(
    name="sfxx", aliases=("step", "sfxx-coding-plan"), default_aux_model="step-3.5-flash",
    env_vars=("SFXX_API_KEY",), base_url="https://api.sfxx.ai/step_plan/v1",
)

register_provider(sfxx)
