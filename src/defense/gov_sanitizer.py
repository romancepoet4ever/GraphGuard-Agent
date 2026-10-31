from __future__ import annotations

import re


def sanitize_text(text: str, level: str = "standard") -> dict:
    replacements = []

    def replace(pattern: str, repl: str, category: str, value: str) -> str:
        replacements.append({"category": category, "original": value, "replacement": repl})
        return repl

    sanitized = re.sub(r"1[3-9]\d{9}", lambda m: replace("", "手机号[已脱敏]", "phone", m.group(0)), text)
    sanitized = re.sub(r"\d{17}[\dXx]", lambda m: replace("", "身份证号[已脱敏]", "id_card", m.group(0)), sanitized)
    sanitized = re.sub(r"(\d+(?:\.\d+)?)(万元|元)", lambda m: replace("", "金额[区间化]", "amount", m.group(0)), sanitized)

    return {
        "sanitized_text": sanitized,
        "level": level,
        "replacements": replacements,
    }
