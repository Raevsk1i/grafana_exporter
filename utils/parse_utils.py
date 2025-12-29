# utils/parse_utils.py

from datetime import datetime

def parse_date(date_to_parse: str):
    """
    Матчит string с нужными форматами даты.
    """
    if date_to_parse.__contains__('now'):
        return date_to_parse
    else:
        if date_to_parse.isdigit():
            return date_to_parse
        return '{}000'.format(
            int(datetime.strptime(date_to_parse, '%d.%m.%Y %H:%M').timestamp())
        )