import re

__all__ = ["MARKDOWN_LINK", "HTML_HREF", "DOI"]

MARKDOWN_LINK = re.compile(r"\[(.*?)\]\((.*?)\)")
HTML_HREF = re.compile(r"<a\s+href=", re.IGNORECASE)
DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
