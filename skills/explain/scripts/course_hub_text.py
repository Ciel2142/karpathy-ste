"""The generated text of the course hub, in the two languages of the lesson rung: `en` and `ru`.

English text is STE-80. Russian text follows SKILL.md convention 7: the structural STE rules
only (short sentences, active voice); English terms and code names go in `<code>` by the
caller. Any other `lang` falls back to `en`. Values that hold `{...}` are format strings.

`plural(lang, key, n)` returns the counted noun phrase, for example "2 steps" or "2 шага".
A Russian key has three forms: one (1, 21, ...), few (2-4, 22-24, ...), many (the rest).
"""

PLURALS = {
    "en": {
        "step": ("step", "steps"),                      # "covers 2 steps"
        "step_nom": ("step", "steps"),                  # "The path: 2 steps"
        "failure": ("failure path", "failure paths"),
        "failure_nom": ("failure path", "failure paths"),
        "part_in": ("part", "parts"),                   # "in 2 parts"
    },
    "ru": {
        "step": ("шаг", "шага", "шагов"),
        "step_nom": ("шаг", "шага", "шагов"),
        "failure": ("ветку ошибки", "ветки ошибки", "веток ошибки"),
        "failure_nom": ("ветка ошибки", "ветки ошибки", "веток ошибки"),
        "part_in": ("части", "частях", "частях"),
    },
}

TEXT = {
    "en": {
        "short": "Short answer.",
        "lead": "The path has {steps} and {failures}, in {parts}.",
        "block": "Part {n}, <q>{title}</q>, {what}.",
        "covers": "covers {what}",
        "main": "{steps} from <code>{start}</code> to <code>{end}</code>",
        "and": "{main} and {failures}",
        "no_step": "covers no step",
        "nav_flow": "Flow",
        "flow_h2": "Which steps make the path?",
        "caption": ("Each box is one step. The main steps go from left to right. A failure path "
                    "goes down from its step. The border shows the evidence. A box with a link "
                    "opens its lesson. A box without a lesson shows <q>not built</q>."),
        "list_intro": "Each step of the path, with its source lines:",
        "not_built": "not built",
        "on_failure": "on failure",
        "legend": "evidence:",
        "evidence": {"code": "code", "docs": "docs", "inferred": "inferred"},
        "svg_title": "The path: {steps} and {failures}",
        "hop_evidence": "evidence",
        "hop_branch": "on failure of",
        "lesson": "lesson",
        "steps": "steps",
        "status": "status",
        "reason": "reason:",
        "none": "none",
        "subject": "Subject",
        "subject_kind": "(course)",
        "root": "Root",
        "source": "Source",
        "commit": "commit",
        "dirty": "dirty",
        "dirty_values": ("no", "dirty"),
        "moved": "moved after planning",
        "date": "Date",
        "review": "Review",
        "review_values": ("off", "on"),
        "not_covered": "Not covered:",
        "sources": "Sources",
    },
    "ru": {
        "short": "Краткий ответ.",
        "lead": "Путь содержит {steps} и {failures} в {parts}.",
        "block": "Часть {n}, <q>{title}</q>, {what}.",
        "covers": "охватывает {what}",
        "main": "{steps} от <code>{start}</code> до <code>{end}</code>",
        "and": "{main} и {failures}",
        "no_step": "не охватывает ни одного шага",
        "nav_flow": "Схема",
        "flow_h2": "Из каких шагов состоит путь?",
        "caption": ("Каждый блок схемы — один шаг. Основные шаги идут слева направо. Ветка "
                    "ошибки идёт вниз от своего шага. Рамка показывает основание шага. Блок со "
                    "ссылкой открывает свой урок. Блок без урока показывает <q>не готово</q>."),
        "list_intro": "Каждый шаг пути и его строки в источнике:",
        "not_built": "не готово",
        "on_failure": "при ошибке",
        "legend": "основание:",
        "evidence": {"code": "код", "docs": "документы", "inferred": "вывод"},
        "svg_title": "Путь: {steps} и {failures}",
        "hop_evidence": "основание",
        "hop_branch": "при ошибке шага",
        "lesson": "урок",
        "steps": "шаги",
        "status": "статус",
        "reason": "причина:",
        "none": "нет",
        "subject": "Тема",
        "subject_kind": "(курс)",
        "root": "Корень",
        "source": "Источник",
        "commit": "коммит",
        "dirty": "изменения",
        "dirty_values": ("нет", "есть"),
        "moved": "сдвинут после планирования",
        "date": "Дата",
        "review": "Ревью",
        "review_values": ("выкл", "вкл"),
        "not_covered": "Не покрыто:",
        "sources": "Источники",
    },
}


def language(lang):
    """The table key for a course `lang`: `ru` or `en` (the fallback)."""
    return lang if lang in TEXT else "en"


def plural(lang, key, count):
    """`count` and its noun in the form that agrees with it."""
    forms = PLURALS[language(lang)][key]
    if len(forms) == 2:
        return "%d %s" % (count, forms[0] if count == 1 else forms[1])
    tens, units = count % 100, count % 10
    if units == 1 and tens != 11:
        form = forms[0]
    elif 2 <= units <= 4 and not 12 <= tens <= 14:
        form = forms[1]
    else:
        form = forms[2]
    return "%d %s" % (count, form)
