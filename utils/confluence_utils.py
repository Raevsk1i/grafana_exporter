# /utils/confluence_utils.py

def escape_html(text: str) -> str:
    """
    Простая защита от XSS: экранируем основные HTML-символы.
    """
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#x27;')
    )