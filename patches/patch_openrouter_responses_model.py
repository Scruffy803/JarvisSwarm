"""Fix reasoning parameter conflicts when using GPT models through OpenRouter.

Two bugs in the Agency Swarm framework:

1. _apply_client_to_agent keeps OpenAIResponsesModel when only base_url/api_key are changed
   at runtime (no model name in the override). OpenRouter doesn't support the Responses API,
   so sending it there causes a double-serialization of reasoning params.

2. _apply_request_model_settings_extra_args moves extra_body from model_settings_extra_args
   onto current.extra_body without checking for a nested 'reasoning' key. If extra_body
   contains {"reasoning": {"effort": "X"}} while model_settings.reasoning.effort is "Y",
   both forms end up in the HTTP request with conflicting values:
     - reasoning_effort: "Y"  (from model_settings.reasoning → Chat Completions path)
     - reasoning: {effort: "X"}  (from extra_body → merged into request body by OpenAI SDK)
"""

from __future__ import annotations


def apply_openrouter_responses_model_patch() -> None:
    try:
        from agency_swarm.integrations.fastapi_utils import endpoint_handlers as _eh
        from agency_swarm.utils.openrouter import OPENROUTER_BASE_URL, build_openrouter_chat_model
        from agents.models.openai_responses import OpenAIResponsesModel
        from agents.model_settings import ModelSettings
        from openai.types.shared import Reasoning
    except Exception:
        return

    if getattr(_eh, "_openswarm_openrouter_patched", False):
        return

    # --- apply client to agent ---

    _orig_apply_client = _eh._apply_client_to_agent

    def _patched_apply_client(agent, client, config):
        _orig_apply_client(agent, client, config)

        if (
            client is not None
            and isinstance(agent.model, OpenAIResponsesModel)
            and str(client.base_url).rstrip("/") == OPENROUTER_BASE_URL.rstrip("/")
        ):
            agent.model = build_openrouter_chat_model(
                agent.model.model,
                openai_client=client,
            )

    _eh._apply_client_to_agent = _patched_apply_client

    # --- apply request model settings extra args ---

    _orig_apply_extra_args = _eh._apply_request_model_settings_extra_args

    def _patched_apply_extra_args(agent, config):
        _orig_apply_extra_args(agent, config)

        ms: ModelSettings | None = getattr(agent, "model_settings", None)
        if ms is None:
            return

        # If extra_body has a nested 'reasoning' key, merge it into model_settings.reasoning
        # so only one form (reasoning_effort) is sent to the Chat Completions API.
        if not isinstance(ms.extra_body, dict) or "reasoning" not in ms.extra_body:
            return

        extra_body = dict(ms.extra_body)
        raw = extra_body.pop("reasoning", None)
        if isinstance(raw, dict):
            effort = raw.get("effort")
            summary = raw.get("summary")
            if effort is not None or summary is not None:
                ms.reasoning = Reasoning(effort=effort, summary=summary)
        ms.extra_body = extra_body or None

    _eh._apply_request_model_settings_extra_args = _patched_apply_extra_args

    _eh._openswarm_openrouter_patched = True
