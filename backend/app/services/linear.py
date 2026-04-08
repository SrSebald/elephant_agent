from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.teams import TeamConfig, get_team_catalog


@dataclass(slots=True)
class LinearIssueResult:
    id: str
    identifier: str
    url: str | None
    dry_run: bool = False


class LinearService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.team_catalog = get_team_catalog(settings)

    def get_team_target(self, team_slug: str) -> TeamConfig:
        return self.team_catalog.get(team_slug, self.team_catalog["backend"])

    async def create_issue(
        self,
        *,
        title: str,
        team_slug: str,
        priority: str,
        description: str,
    ) -> LinearIssueResult:
        team = self.get_team_target(team_slug)
        if not self.settings.linear_api_key or not team.linear_team_id:
            if self.settings.allow_dry_run:
                token = uuid4().hex[:8].upper()
                return LinearIssueResult(
                    id=f"dry-run-{token}",
                    identifier=f"DRY-{token}",
                    url=None,
                    dry_run=True,
                )
            raise RuntimeError(
                f"Linear is not configured for team '{team.slug}'. Set LINEAR_API_KEY and the team id."
            )

        query = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              url
            }
          }
        }
        """
        variables = {
            "input": {
                "title": title,
                "description": description,
                "teamId": team.linear_team_id,
                "priority": self._map_priority(priority),
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                headers={
                    "Authorization": self.settings.linear_api_key,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()

        payload = response.json()
        errors = payload.get("errors")
        if errors:
            raise RuntimeError(errors[0].get("message", "Linear issue creation failed."))

        issue = payload["data"]["issueCreate"]["issue"]
        return LinearIssueResult(
            id=issue["id"],
            identifier=issue["identifier"],
            url=issue.get("url"),
        )

    @staticmethod
    def _map_priority(priority: str) -> int:
        return {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
        }.get(priority, 3)
