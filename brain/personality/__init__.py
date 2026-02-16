"""OutBot personality: loading memory files and formatting WhatsApp messages."""

from brain.personality.loader import PersonalityLoader
from brain.personality.formatter import format_outbound, format_for_whatsapp

__all__ = ["PersonalityLoader", "format_outbound", "format_for_whatsapp"]
