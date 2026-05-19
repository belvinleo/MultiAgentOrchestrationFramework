"""
web_search.py
-------------
Web search tool using DuckDuckGo — completely free, no API key needed.
Used by Finance (news), Library (research), and General departments.
"""

from duckduckgo_search import DDGS
from datetime import datetime


class WebSearch:
    """
    Searches the web and returns clean, summarized results.
    All agents can use this to get current information.
    """

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str, max_results: int = None) -> list:
        """
        Search the web for a query.

        Parameters:
            query       : the search query
            max_results : override default max results

        Returns:
            list of dicts with title, url, snippet
        """
        limit = max_results or self.max_results
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=limit,
                    region="in-en",  # India-first results
                ))
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def search_news(self, query: str, max_results: int = 5) -> list:
        """
        Search for recent news articles.

        Parameters:
            query : news topic to search

        Returns:
            list of news items with title, url, date, source
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(
                    query,
                    max_results=max_results,
                    region="in-en",
                ))
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def format_for_agent(self, results: list, max_chars: int = 2000) -> str:
        """
        Convert raw search results into clean text an agent can read.

        Parameters:
            results   : list of search result dicts
            max_chars : truncate output to this length

        Returns:
            Formatted string of search results
        """
        if not results:
            return "No results found."

        if results and "error" in results[0]:
            return f"Search failed: {results[0]['error']}"

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body") or r.get("snippet", "")
            url = r.get("url") or r.get("href", "")
            date = r.get("date", "")

            lines.append(f"[{i}] {title}")
            if date:
                lines.append(f"    Date: {date}")
            if body:
                lines.append(f"    {body[:200]}")
            if url:
                lines.append(f"    Source: {url}")
            lines.append("")

        output = "\n".join(lines)
        return output[:max_chars] if len(output) > max_chars else output