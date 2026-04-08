import base64

import httpx

from app.core.config import Settings
from app.schemas.analysis import RelevantFile


class GitHubService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def search_code(self, search_terms: list[str], limit: int = 5) -> list[RelevantFile]:
        if not self.settings.github_token or not self._repositories:
            return []

        unique_terms = [term.strip() for term in search_terms if term.strip()]
        if not unique_terms:
            return []

        collected: list[RelevantFile] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for repository in self._repositories:
                query = f"{' '.join(unique_terms[:4])} repo:{repository}"
                response = await client.get(
                    "https://api.github.com/search/code",
                    params={"q": query, "per_page": min(limit, 5)},
                    headers=self._headers,
                )
                if response.status_code >= 400:
                    continue

                for item in response.json().get("items", []):
                    content_excerpt = await self._fetch_file_excerpt(client, item.get("url"))
                    collected.append(
                        RelevantFile(
                            repository=item["repository"]["full_name"],
                            path=item["path"],
                            url=item.get("html_url"),
                            snippet=content_excerpt[:220],
                            content_excerpt=content_excerpt,
                        )
                    )
                    if len(collected) >= limit:
                        return collected

        return collected

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def _repositories(self) -> list[str]:
        repositories: list[str] = []
        for repo in self.settings.github_repositories:
            if "/" in repo or not self.settings.github_owner:
                repositories.append(repo)
            else:
                repositories.append(f"{self.settings.github_owner}/{repo}")
        return repositories

    async def _fetch_file_excerpt(self, client: httpx.AsyncClient, url: str | None) -> str:
        if not url:
            return ""

        response = await client.get(url, headers=self._headers)
        if response.status_code >= 400:
            return ""

        content = response.json().get("content", "")
        if not content:
            return ""

        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        return decoded[:1600]
