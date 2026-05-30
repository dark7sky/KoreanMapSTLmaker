from __future__ import annotations

from typing import Iterable

HEIGHT_FIELD_TOKENS: tuple[str, ...] = (
    "height",
    "buildingheight",
    "buildheight",
    "bldgh",
    "bldg_h",
    "hgt",
    "\ub192\uc774",
    "\uac74\ubb3c\ub192\uc774",
    "\uce35\uace0",
    "\uace0\ub3c4",
)

FLOOR_FIELD_TOKENS: tuple[str, ...] = (
    "floor",
    "floors",
    "stories",
    "storey",
    "story",
    "level",
    "levels",
    "grnd_flr",
    "\uce35\uc218",
    "\uc9c0\uc0c1\uce35\uc218",
    "\uc9c0\uc0c1\uce35",
)


def suggest_fields(field_names: Iterable[str], kind: str, top_n: int = 5) -> tuple[str, ...]:
    tokens = HEIGHT_FIELD_TOKENS if kind == "height" else FLOOR_FIELD_TOKENS
    scored = []
    for field in field_names:
        name = str(field)
        score = _score_field_name(name, tokens)
        if score > 0:
            scored.append((score, name))
    scored.sort(key=lambda item: (-item[0], item[1].lower()))
    return tuple(name for _, name in scored[: max(top_n, 0)])


def _score_field_name(field_name: str, tokens: tuple[str, ...]) -> int:
    normalized = _normalize(field_name)
    if not normalized:
        return 0

    best = 0
    for token in tokens:
        token_normalized = _normalize(token)
        if not token_normalized:
            continue
        if normalized == token_normalized:
            best = max(best, 100)
            continue
        if normalized.startswith(token_normalized) or normalized.endswith(token_normalized):
            best = max(best, 80)
            continue
        if token_normalized in normalized:
            best = max(best, 60)
    return best


def _normalize(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())
