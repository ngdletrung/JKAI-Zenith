import re

class ResponseFilter:
    @staticmethod
    def strip_emoji(text: str) -> str:
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002300-\U000027BF"
            "\U0000FE00-\U0000FE0F"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U0000200D\u200B\u200C"
            "\U0000FE0F" "]+", flags=re.UNICODE)
        return emoji_pattern.sub("", text).strip()

    @staticmethod
    def remove_code_block(text: str) -> str:
        return re.sub(r'```[\s\S]*?```', '', text).strip()

    @staticmethod
    def enforce_contract(text: str, lang: str = "vi") -> str:
        if lang == "vi":
            if not any(w in text.lower() for w in ["master", "ngài"]):
                text = text.lstrip()
        return text

response_filter = ResponseFilter()
