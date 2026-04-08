import json
import re
from collections import Counter
from typing import Iterable

import httpx

from app.core.config import Settings
from app.core.teams import get_team_catalog
from app.schemas.analysis import ExtractionSignal, RelevantFile, TicketAnalysis

STOP_WORDS = {
    "the",
    "and",
    "that",
    "with",
    "from",
    "this",
    "were",
    "into",
    "have",
    "http",
    "https",
    "para",
    "como",
    "pero",
    "cuando",
    "desde",
    "error",
    "ticket",
    "issue",
    "agent",
    "report",
    "reporte",
    "need",
    "just",
}


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.team_catalog = get_team_catalog(settings)

    async def extract_signal(self, *, report_text: str, file_content: str) -> ExtractionSignal:
        if not self.settings.openai_api_key:
            return self._fallback_signal(report_text, file_content)

        prompt = f"""
Return valid JSON with the keys:
- category: one of ["bug", "incident", "config"]
- keywords: list of up to 6 short technical keywords
- components: list of up to 4 components or services
- search_queries: list of up to 4 GitHub code search strings

Ticket report:
{report_text}

Attachment excerpt:
{file_content[:2000]}
"""
        try:
            payload = await self._chat_json(
                system_prompt="You extract technical routing signals from incident reports. Respond with JSON only.",
                user_prompt=prompt,
            )
            return ExtractionSignal.model_validate(payload)
        except Exception:
            return self._fallback_signal(report_text, file_content)

    async def analyze_report(
        self,
        *,
        title: str,
        report_text: str,
        file_content: str,
        relevant_files: list[RelevantFile],
    ) -> TicketAnalysis:
        if not self.settings.openai_api_key:
            return self._fallback_analysis(title, report_text, file_content, relevant_files)

        code_context = "\n\n".join(
            f"Repository: {item.repository}\nPath: {item.path}\nSnippet:\n{item.content_excerpt[:1200]}"
            for item in relevant_files
        ) or "No GitHub matches found."

        prompt = f"""
Return valid JSON with the keys:
- category: one of ["bug", "incident", "config"]
- summary: short executive summary
- diagnosis: concise technical diagnosis
- resolution_path: markdown paragraph explaining the best initial fix path
- assigned_team: one of ["backend", "frontend", "infra"]
- priority: one of ["low", "medium", "high", "critical"]
- keywords: list of up to 6 keywords
- components: list of up to 4 components
- next_steps: list of 3 concrete actions
- confidence: float from 0 to 1
- execution_mode: "live"

Ticket title:
{title}

Ticket report:
{report_text}

Attachment excerpt:
{file_content[:2400]}

Relevant code context:
{code_context}
"""
        try:
            payload = await self._chat_json(
                system_prompt=(
                    "You are an incident triage agent. Decide the best team, summarize the issue, "
                    "and produce JSON only."
                ),
                user_prompt=prompt,
            )
            return TicketAnalysis.model_validate(payload)
        except Exception:
            return self._fallback_analysis(title, report_text, file_content, relevant_files)

    async def _chat_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.openai_model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(self._strip_code_fences(content))

    def _fallback_signal(self, report_text: str, file_content: str) -> ExtractionSignal:
        combined = f"{report_text}\n{file_content}"
        keywords = self._top_keywords(combined, limit=6)
        category = self._classify_category(combined)
        components = [keyword for keyword in keywords if "/" in keyword or "-" in keyword][:4]
        search_queries = keywords[:4]
        return ExtractionSignal(
            category=category,
            keywords=keywords,
            components=components,
            search_queries=search_queries,
        )

    def _fallback_analysis(
        self,
        title: str,
        report_text: str,
        file_content: str,
        relevant_files: list[RelevantFile],
    ) -> TicketAnalysis:
        combined = f"{title}\n{report_text}\n{file_content}\n" + "\n".join(
            f"{item.repository} {item.path} {item.content_excerpt}" for item in relevant_files
        )
        category = self._classify_category(combined)
        assigned_team = self._classify_team(combined)
        priority = self._classify_priority(combined, category)
        keywords = self._top_keywords(combined, limit=6)
        components = [item.path.split("/")[0] for item in relevant_files[:4]]
        repo_summary = ", ".join(f"{item.repository}/{item.path}" for item in relevant_files[:3]) or "No GitHub matches yet"

        summary = f"{category.title()} report routed to {assigned_team} based on the current incident signals."
        diagnosis = (
            f"The report suggests impact around {', '.join(keywords[:3]) or 'the reported component'}. "
            f"Most relevant code context: {repo_summary}."
        )
        resolution_path = (
            "Validate the failing path, reproduce the issue with the attached context, "
            "and inspect the matched repository files before applying a targeted fix."
        )
        next_steps = [
            "Reproduce the report with the provided description and attachment.",
            "Inspect the matched code paths and confirm the owning team.",
            "Create the first fix or mitigation task in Linear and notify the team.",
        ]

        return TicketAnalysis(
            category=category,
            summary=summary,
            diagnosis=diagnosis,
            resolution_path=resolution_path,
            assigned_team=assigned_team,
            priority=priority,
            keywords=keywords,
            components=[component for component in components if component],
            next_steps=next_steps,
            confidence=round(min(0.55 + (0.08 * len(relevant_files)), 0.9), 2),
            execution_mode="dry-run",
        )

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned).strip()
        return cleaned

    def _classify_category(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("deploy", "env ", "config", "terraform", "kubernetes")):
            return "config"
        if any(token in lowered for token in ("outage", "down", "incident", "unavailable", "latency spike")):
            return "incident"
        return "bug"

    def _classify_priority(self, text: str, category: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("critical", "sev1", "outage", "payment", "login down", "checkout")):
            return "critical"
        if category == "incident" or any(token in lowered for token in ("500", "timeout", "prod", "failed")):
            return "high"
        if any(token in lowered for token in ("slow", "warning", "degraded")):
            return "medium"
        return "medium"

    def _classify_team(self, text: str) -> str:
        lowered = text.lower()
        scores: dict[str, int] = {slug: 0 for slug in self.team_catalog}
        for slug, team in self.team_catalog.items():
            scores[slug] += self._keyword_score(lowered, team.keywords)
            scores[slug] += self._keyword_score(lowered, team.repo_hints)
        return max(scores, key=scores.get)

    @staticmethod
    def _keyword_score(text: str, tokens: Iterable[str]) -> int:
        return sum(2 for token in tokens if token in text)

    def _top_keywords(self, text: str, limit: int = 6) -> list[str]:
        tokens = re.findall(r"[A-Za-z0-9_./-]{4,}", text.lower())
        counter = Counter(token for token in tokens if token not in STOP_WORDS)
        return [token for token, _ in counter.most_common(limit)]
