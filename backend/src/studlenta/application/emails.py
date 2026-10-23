"""Шаблон писем: текстовая и HTML-версии с одной кнопкой-ссылкой."""

from html import escape

_BUTTON = (
    "display:inline-block;padding:12px 20px;background:#2B59E0;color:#FFFFFF;"
    "border-radius:10px;text-decoration:none;font-weight:600"
)


def letter(name: str, intro: str, link: str, button: str, note: str) -> tuple[str, str]:
    text = f"{name}, здравствуйте!\n\n{intro}\n{link}\n\n{note}\n"
    html = (
        f"<p>{escape(name)}, здравствуйте!</p>"
        f"<p>{escape(intro)}</p>"
        f'<p><a href="{escape(link)}" style="{_BUTTON}">{escape(button)}</a></p>'
        f'<p style="color:#4B5563">Или откройте ссылку: {escape(link)}<br>{escape(note)}</p>'
    )
    return text, html
