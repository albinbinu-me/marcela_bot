from unidecode import unidecode


def normalize(text):
    if not text:
        return ""
    return unidecode(text).lower().strip()
