import re

__all__ = [
    "THINK_TAG", "ANALYSIS_TAG", "REFLECTION_TAG",
    "CRITIC_TAG", "TOOL_CALL_TAG", "XML_TAG",
    "strip_think_tags", "strip_ai_tags",
]

THINK_TAG = re.compile(r"<think>\s*(.*?)\s*(?:</think>|$)", re.DOTALL)
ANALYSIS_TAG = re.compile(r"<analysis>[\s\S]*?</analysis>")
REFLECTION_TAG = re.compile(r"<reflection>[\s\S]*?</reflection>")
CRITIC_TAG = re.compile(r"<critic>[\s\S]*?</critic>")
TOOL_CALL_TAG = re.compile(r"<tool_call>[\s\S]*?</tool_call>")
XML_TAG = re.compile(r"<\w+>[\s\S]*?</\w+>")


def strip_think_tags(text: str) -> str:
    return THINK_TAG.sub("", text).strip()


def strip_ai_tags(text: str) -> str:
    for tag in (THINK_TAG, ANALYSIS_TAG, REFLECTION_TAG, CRITIC_TAG):
        text = tag.sub("", text)
    return text.strip()
