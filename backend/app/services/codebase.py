import asyncio
import subprocess
from pathlib import Path

from app.core.config import Settings
from app.schemas.analysis import RelevantFile

SEARCHABLE_SUFFIXES = {
    ".rb",
    ".erb",
    ".rake",
    ".yml",
    ".yaml",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".scss",
    ".md",
}

SKIP_DIRECTORIES = {
    ".git",
    "tmp",
    "log",
    "node_modules",
    "vendor",
    "coverage",
}


class SolidusCodebaseService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repo_path = settings.solidus_repo_path
        self._clone_lock = asyncio.Lock()

    async def ensure_repo(self) -> None:
        if self._looks_ready():
            return

        if not self.settings.solidus_auto_clone:
            return

        async with self._clone_lock:
            if self._looks_ready():
                return
            await asyncio.to_thread(self._clone_repo_sync)

    async def search_code(self, search_terms: list[str], limit: int = 5) -> list[RelevantFile]:
        await self.ensure_repo()
        if not self._looks_ready():
            return []
        return await asyncio.to_thread(self._search_sync, search_terms, limit)

    def _looks_ready(self) -> bool:
        return self.repo_path.exists() and (self.repo_path / ".git").exists()

    def _clone_repo_sync(self) -> None:
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        if self.repo_path.exists() and any(self.repo_path.iterdir()):
            return

        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                self.settings.solidus_repo_branch,
                self.settings.solidus_repo_url,
                str(self.repo_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def _search_sync(self, search_terms: list[str], limit: int) -> list[RelevantFile]:
        normalized_terms = [term.lower().strip() for term in search_terms if term.strip()]
        if not normalized_terms:
            normalized_terms = ["checkout", "order", "payment"]

        matches: list[RelevantFile] = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SEARCHABLE_SUFFIXES:
                continue
            if any(part in SKIP_DIRECTORIES for part in file_path.parts):
                continue

            relative_path = file_path.relative_to(self.repo_path).as_posix()
            try:
                content = file_path.read_text("utf-8", errors="ignore")
            except OSError:
                continue

            lowered_path = relative_path.lower()
            lowered_content = content.lower()
            score = 0.0
            for term in normalized_terms:
                if term in lowered_path:
                    score += 4.0
                occurrences = lowered_content.count(term)
                score += float(min(occurrences, 4))

            if score <= 0:
                continue

            matches.append(
                RelevantFile(
                    repository="solidusio/solidus",
                    path=relative_path,
                    url=self._build_github_url(relative_path),
                    snippet=self._excerpt(content, normalized_terms),
                    content_excerpt=content[:1800],
                    score=score,
                )
            )

        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:limit]

    def _build_github_url(self, relative_path: str) -> str:
        repo_url = self.settings.solidus_repo_url.removesuffix(".git")
        return f"{repo_url}/blob/{self.settings.solidus_repo_branch}/{relative_path}"

    @staticmethod
    def _excerpt(content: str, search_terms: list[str]) -> str:
        lowered = content.lower()
        for term in search_terms:
            position = lowered.find(term)
            if position >= 0:
                start = max(position - 120, 0)
                end = min(position + 220, len(content))
                return content[start:end].replace("\n", " ").strip()
        return content[:220].replace("\n", " ").strip()
