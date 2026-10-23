#!/usr/bin/env python3
"""Проверяет Conventional Commits: ``тип(область): описание``. См. CONTRIBUTING.md.

Используется как commit-msg хук и в CI (сообщения передаются построчно через --stdin).
"""

import re
import sys

TYPES = "feat|fix|test|refactor|docs|chore|build|ci|perf|style|revert"
PATTERN = re.compile(rf"^({TYPES})(\([a-z0-9-]+\))?!?: \S.{{0,99}}$")
SKIP = re.compile(r"^(Merge |Revert \"|fixup! |squash! )")


def check(subject: str) -> str | None:
    if SKIP.match(subject) or PATTERN.match(subject):
        return None
    return (
        f"Некорректный заголовок коммита: {subject!r}\n"
        f"Ожидается «тип(область): описание», тип из: {TYPES.replace('|', ', ')}.\n"
        "Пример: feat(moderation): возврат заявки с комментарием"
    )


def main() -> int:
    if sys.argv[1:] == ["--stdin"]:
        subjects = [line.strip() for line in sys.stdin if line.strip()]
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            subjects = [f.readline().strip()]
    errors = [e for s in subjects if (e := check(s))]
    print("\n\n".join(errors), file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
