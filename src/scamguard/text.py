import re
import unicodedata

import numpy as np


def normalize_text(text: str) -> str:
    """Normalize spacing and Unicode consistently in training and inference."""
    value = unicodedata.normalize("NFKC", str(text)).casefold()
    value = value.replace("\u200b", " ").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_batch(values):
    return np.asarray([normalize_text(value) for value in values], dtype=object)
