"""Japanese number data and conversion for numbers 1 through 100."""
from __future__ import annotations

from functools import lru_cache

_UNITS = {
    1: ("いち", "ichi", "一"),
    2: ("に", "ni", "二"),
    3: ("さん", "san", "三"),
    4: ("よん", "yon", "四"),
    5: ("ご", "go", "五"),
    6: ("ろく", "roku", "六"),
    7: ("なな", "nana", "七"),
    8: ("はち", "hachi", "八"),
    9: ("きゅう", "kyuu", "九"),
}
_TENS = {
    2: ("にじゅう", "nijuu", "二十"),
    3: ("さんじゅう", "sanjuu", "三十"),
    4: ("よんじゅう", "yonjuu", "四十"),
    5: ("ごじゅう", "gojuu", "五十"),
    6: ("ろくじゅう", "rokujuu", "六十"),
    7: ("ななじゅう", "nanajuu", "七十"),
    8: ("はちじゅう", "hachijuu", "八十"),
    9: ("きゅうじゅう", "kyuujuu", "九十"),
}


@lru_cache(maxsize=100)
def number_details(number: int) -> dict[str, int | str]:
    """Return kanji, hiragana, and Romaji for a number in the supported range.

    Readings use beginner-friendly variants: yon (4), nana (7), kyuu (9).
    """
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 100:
        raise ValueError("number must be an integer between 1 and 100")

    if number == 100:
        hiragana, romaji, kanji = "ひゃく", "hyaku", "百"
    elif number == 10:
        hiragana, romaji, kanji = "じゅう", "juu", "十"
    elif number < 10:
        hiragana, romaji, kanji = _UNITS[number]
    elif number < 20:
        unit = number - 10
        hiragana = "じゅう" + _UNITS[unit][0]
        romaji = "juu" + _UNITS[unit][1]
        kanji = "十" + _UNITS[unit][2]
    else:
        tens, unit = divmod(number, 10)
        hiragana, romaji, kanji = _TENS[tens]
        if unit:
            hiragana += _UNITS[unit][0]
            romaji += _UNITS[unit][1]
            kanji += _UNITS[unit][2]
    return {"number": number, "kanji": kanji, "hiragana": hiragana, "romaji": romaji}


def all_numbers() -> list[dict[str, int | str]]:
    return [number_details(number) for number in range(1, 101)]
