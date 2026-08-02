import re

__all__ = [
    "URL", "GIT_URL", "EMAIL", "PHONE", "PHONE_VN",
    "IPV4", "IPV6", "UUID4", "SEMVER", "MAC_ADDRESS", "ISBN",
    "PY_FILE", "IMAGE_HINT", "HASHTAG", "WIKI_LINK",
]

URL = re.compile(r"https?://[^\s`\"'<>]+", re.IGNORECASE)
GIT_URL = re.compile(
    r"https?://(?:www\.)?(?:github|gitlab|bitbucket)\.com/", re.IGNORECASE
)
EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE = re.compile(r"\b\d{4}[-.]?\d{3}[-.]?\d{3}\b")
PHONE_VN = re.compile(r"(0|\+84)\d{9}")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6 = re.compile(
    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}"
    r"|[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}"
    r"|:(?::[0-9a-fA-F]{1,4}){1,7}"
    r"|::"
)
UUID4 = re.compile(
    r"[a-fA-F0-9]{8}-"
    r"[a-fA-F0-9]{4}-"
    r"4[a-fA-F0-9]{3}-"
    r"[89abAB][a-fA-F0-9]{3}-"
    r"[a-fA-F0-9]{12}"
)
SEMVER = re.compile(
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?"
)
MAC_ADDRESS = re.compile(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}")
ISBN = re.compile(
    r"(?:ISBN(?:-1[03])?:? )?"
    r"(?=[0-9X]{10}$|(?=(?:[0-9]+[- ]){3})[- 0-9X]{13}$|"
    r"97[89][0-9]{10}$|(?=(?:[0-9]+[- ]){4})[- 0-9]{17}$)"
    r"(?:97[89][- ]?)?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9X]"
)
PY_FILE = re.compile(r"\b((?:[\w\-]+/)*[\w\-]+\.py)\b", re.IGNORECASE)
IMAGE_HINT = re.compile(
    r"\b(hình|hinh|ảnh|anh|image|vision|screenshot|ocr)\b", re.IGNORECASE
)
HASHTAG = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_]*)")
WIKI_LINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
