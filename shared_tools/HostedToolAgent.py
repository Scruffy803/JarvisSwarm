"""Base Agent class that swaps BaseTool fallbacks for OAI hosted tools on the Responses API."""

from agency_swarm import Agent
from agency_swarm.tools import WebSearchTool
from agents import RunContextWrapper

from shared_tools.WebSearch import WebSearch


class HostedToolAgent(Agent):
    """Agent that dynamically routes hosted tools at call time.

    At each request, get_all_tools() checks the live model type:
    - OpenAIResponsesModel: replaces each BaseTool named in _hosted_tool_map
      with its hosted counterpart (in-place, same position in list).
    - Completions / LiteLLM: returns the list unchanged (BaseTool only, no errors).

    Subclasses can extend _hosted_tool_map for additional swaps.
    The static tools list should always contain the BaseTool fallbacks.
    """

    _hosted_tool_map: dict = {
        "WebSearch": WebSearchTool(search_context_size="high"),
    }

    async def get_all_tools(self, run_context: RunContextWrapper) -> list:
        tools = await super().get_all_tools(run_context)

        if not self._hosted_tool_map:
            return tools

        try:
            from agents import OpenAIResponsesModel
            if isinstance(self.model, OpenAIResponsesModel):
                tools = [
                    self._hosted_tool_map.get(getattr(t, "name", None), t)
                    for t in tools
                ]
        except ImportError:
            pass

        return tools
