import base64
import hashlib
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from string import printable
from typing import Sequence

from fastapi import UploadFile

from app.core.config import Settings
from app.schemas.analysis import AttachmentArtifact, GuardrailFinding

TEXT_EXTENSIONS = {".txt", ".md", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROMPT_INJECTION_PATTERNS = {
    "ignore previous": "Attachment attempts to override prior instructions.",
    "system prompt": "Attachment references hidden system prompts.",
    "developer message": "Attachment references developer-only instructions.",
    "tool call": "Attachment contains tool manipulation language.",
    "api key": "Attachment references secrets or credential exfiltration.",
    "rm -rf": "Attachment contains destructive shell patterns.",
    "curl http": "Attachment suggests network exfiltration commands.",
}


@dataclass(slots=True)
class IngestionResult:
    file_content: str
    attachments: list[AttachmentArtifact]
    guardrail_findings: list[GuardrailFinding]


class IngestionService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def ingest_files(self, files: Sequence[UploadFile]) -> IngestionResult:
        if len(files) > self.settings.max_attachments:
            raise ValueError(f"Only {self.settings.max_attachments} attachments are allowed.")

        rendered_text_blocks: list[str] = []
        attachments: list[AttachmentArtifact] = []
        findings: list[GuardrailFinding] = []
        total_bytes = 0

        for upload in files:
            if not upload.filename:
                continue

            content = await upload.read()
            total_bytes += len(content)
            if len(content) > self.settings.max_upload_bytes:
                raise ValueError(f"{upload.filename} exceeds the per-file size limit.")
            if total_bytes > self.settings.max_total_upload_bytes:
                raise ValueError("Total upload size exceeds the allowed limit.")

            extension = Path(upload.filename).suffix.lower()
            mime_type = upload.content_type or mimetypes.guess_type(upload.filename)[0] or "application/octet-stream"

            if extension in TEXT_EXTENSIONS:
                text = self._decode_text(upload.filename, content)
                prompt_signals = self._detect_prompt_injection(text)
                findings.extend(
                    GuardrailFinding(
                        rule="prompt_injection_scan",
                        severity="warning",
                        message=f"{upload.filename}: {signal}",
                    )
                    for signal in prompt_signals
                )
                sanitized_text = text.replace("\x00", " ").strip()
                rendered_text_blocks.append(f"### {upload.filename}\n{sanitized_text}")
                attachments.append(
                    AttachmentArtifact(
                        filename=upload.filename,
                        kind="text",
                        mime_type="text/plain",
                        size_bytes=len(content),
                        sha256=self._sha256(content),
                        text_excerpt=sanitized_text[:1500],
                        prompt_injection_signals=prompt_signals,
                    )
                )
                continue

            if extension in IMAGE_EXTENSIONS:
                attachments.append(
                    AttachmentArtifact(
                        filename=upload.filename,
                        kind="image",
                        mime_type=mime_type,
                        size_bytes=len(content),
                        sha256=self._sha256(content),
                        data_url=f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}",
                    )
                )
                continue

            raise ValueError("Only .txt, .md, .log, .png, .jpg, .jpeg, and .webp files are allowed.")

        return IngestionResult(
            file_content="\n\n".join(rendered_text_blocks),
            attachments=attachments,
            guardrail_findings=findings,
        )

    def _decode_text(self, filename: str, content: bytes) -> str:
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{filename} is not valid UTF-8 text.") from exc

        printable_chars = sum(1 for character in decoded if character in printable or character in "\n\r\t")
        if decoded and printable_chars / max(len(decoded), 1) < 0.85:
            raise ValueError(f"{filename} looks like a binary file, not plain text.")

        return decoded

    def _detect_prompt_injection(self, text: str) -> list[str]:
        lowered = text.lower()
        return [message for pattern, message in PROMPT_INJECTION_PATTERNS.items() if pattern in lowered]

    @staticmethod
    def _sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
