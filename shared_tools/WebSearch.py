"""Web search via DuckDuckGo — no API key required, works with any provider."""

from __future__ import annotations

import json
from typing import Literal
from agency_swarm.tools import BaseTool
from pydantic import Field


class WebSearch(BaseTool):
    """
    Search the web using DuckDuckGo. Returns titles, URLs, and text snippets.
    Use this to look up facts, research topics, find current information, or locate specific web pages.
    For recent news and current events, set mode='news' and/or timelimit='d' or 'w'.
    No API key required.
    """

    query: str = Field(..., description="Search query")
    num_results: int = Field(default=5, description="Number of results to return (1–10)")
    timelimit: Literal["d", "w", "m", "y"] | None = Field(
        default=None,
        description="Filter by recency: 'd' = past day, 'w' = past week, 'm' = past month, 'y' = past year. Omit for all-time results.",
    )
    mode: Literal["web", "news"] = Field(
        default="web",
        description="'web' for general search, 'news' for recent news articles (includes publication date).",
    )

    def run(self) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            raise ImportError("Run `pip install ddgs` to enable web search.")

        num = max(1, min(self.num_results, 10))
        kwargs = {"max_results": num}
        if self.timelimit:
            kwargs["timelimit"] = self.timelimit

        with DDGS() as ddgs:
            if self.mode == "news":
                raw = list(ddgs.news(self.query, **kwargs))
                results = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("body", ""),
                        "date": r.get("date", ""),
                        "source": r.get("source", ""),
                    }
                    for r in raw
                ]
            else:
                raw = list(ddgs.text(self.query, **kwargs))
                results = [
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                    for r in raw
                ]

        if not results:
            return json.dumps({"query": self.query, "results": [], "note": "No results found."})

        return json.dumps({"query": self.query, "results": results}, indent=2)


if __name__ == "__main__":
    print(WebSearch(query="AI news today", num_results=3, mode="news", timelimit="d").run())
