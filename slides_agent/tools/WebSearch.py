"""Web search via DuckDuckGo — no API key required, works with any provider."""

from __future__ import annotations

import json
from agency_swarm.tools import BaseTool
from pydantic import Field


class WebSearch(BaseTool):
    """
    Search the web using DuckDuckGo. Returns titles, URLs, and text snippets for matching pages.
    Use this to look up facts, research topics, find current information, or locate specific web pages.
    No API key required.
    """

    query: str = Field(..., description="Search query")
    num_results: int = Field(default=5, description="Number of results to return (1–10)")

    def run(self) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            raise ImportError("Run `pip install ddgs` to enable web search.")

        num = max(1, min(self.num_results, 10))
        with DDGS() as ddgs:
            results = list(ddgs.text(self.query, max_results=num))

        if not results:
            return json.dumps({"query": self.query, "results": [], "note": "No results found."})

        return json.dumps({
            "query": self.query,
            "results": [
                {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in results
            ],
        }, indent=2)


if __name__ == "__main__":
    print(WebSearch(query="best practices for AI in 2025", num_results=3).run())
