"""
JKAI Regex Library — modular patterns for cleaning, extraction, security,
validation, intent detection, and AI pipeline tags.

Usage:
    from core.utils.regex import clean_text, URL, THINK_TAG
    from core.utils.regex.locale import vi_vn
"""

from core.utils.regex.cleaning import *
from core.utils.regex.markdown import *
from core.utils.regex.programming import *
from core.utils.regex.json import *
from core.utils.regex.sql import *
from core.utils.regex.security import *
from core.utils.regex.extraction import *
from core.utils.regex.intent import *
from core.utils.regex.validator import *
from core.utils.regex.files import *
from core.utils.regex.datetime import *
from core.utils.regex.logs import *
from core.utils.regex.citations import *
from core.utils.regex.ai_tags import *
from core.utils.regex.dsl import *
from core.utils.regex import locale
