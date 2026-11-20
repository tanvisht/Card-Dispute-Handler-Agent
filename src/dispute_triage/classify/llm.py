"""Claude-backed classifier using forced tool use for schema-valid JSON."""
from __future__ import annotations

import logging
import time

import anthropic

from ..models import Complaint
from .base import Classifier, RawLabel
from .prompts import SYSTEM_PROMPT, TRIAGE_TOOL, user_message

log = logging.getLogger(__name__)


class LLMClassifier(Classifier):
    def __init__(self, settings=None, client: anthropic.Anthropic | None = None):
        super().__init__(settings)
        self.client = client or anthropic.Anthropic(api_key=self.settings.anthropic_api_key, max_retries=4)
        self.name = f"llm:{self.settings.triage_model}"

    def _predict(self, complaint: Complaint) -> RawLabel:
        narrative = complaint.narrative[: self.settings.triage_max_narrative_chars]
        t0 = time.perf_counter()
        resp = self.client.messages.create(
            model=self.settings.triage_model,
            max_tokens=600,
            temperature=0,
            # system prompt is identical across calls -> cache it
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": TRIAGE_TOOL["name"]},
            messages=[{"role": "user", "content": user_message(narrative, complaint.issue, complaint.sub_issue)}],
        )
        log.debug("classified %s in %.2fs", complaint.complaint_id, time.perf_counter() - t0)
        for block in resp.content:
            if block.type == "tool_use":
                return RawLabel(block.input)
        raise RuntimeError(f"no tool_use block for complaint {complaint.complaint_id}")
