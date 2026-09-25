"""Programming languages a step may allow.

Steps store our own stable keys, never Judge0 language ids: ids and versions
differ between Judge0 releases and change on upgrade. A key is mapped to a
Judge0 language at run time from the server's own ``GET /languages`` list,
taking the newest version, so a Judge0 upgrade needs no data migration.
"""

import re
from dataclasses import dataclass
from typing import Any, Literal

Language = Literal["python3", "javascript", "cpp", "csharp", "go", "pascal"]


@dataclass(frozen=True)
class LanguageSpec:
    title: str
    # Matches Judge0 language names such as "Python (3.8.1)".
    judge0_name: re.Pattern[str]


LANGUAGES: dict[Language, LanguageSpec] = {
    "python3": LanguageSpec("Python 3", re.compile(r"^Python \(3\.")),
    "javascript": LanguageSpec("JavaScript (Node.js)", re.compile(r"^JavaScript \(")),
    "cpp": LanguageSpec("C++ (GCC)", re.compile(r"^C\+\+ \(GCC ")),
    "csharp": LanguageSpec("C#", re.compile(r"^C# \(")),
    "go": LanguageSpec("Go", re.compile(r"^Go \(")),
    "pascal": LanguageSpec("Pascal (FPC)", re.compile(r"^Pascal \(")),
}


def _version(name: str) -> tuple[int, ...]:
    # "C++ (GCC 9.2.0)" -> (9, 2, 0); the digits of the language name itself
    # ("Python 3") are outside the parentheses and do not take part.
    return tuple(int(n) for n in re.findall(r"\d+", name.partition("(")[2]))


def resolve_ids(judge0_languages: list[dict[str, Any]]) -> dict[Language, int]:
    """Judge0 id of every supported language that this Judge0 has.

    A language Judge0 does not offer (any more) is simply absent from the
    result: the caller decides what that means.
    """
    ids: dict[Language, int] = {}
    for key, spec in LANGUAGES.items():
        found = [
            lang for lang in judge0_languages if spec.judge0_name.match(lang["name"])
        ]
        if found:
            ids[key] = max(found, key=lambda lang: _version(lang["name"]))["id"]
    return ids
