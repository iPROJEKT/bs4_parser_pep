class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег"""
    pass

class ParserNotFindWersion(Exception):
    """Не найден список c версиями Python"""
    pass