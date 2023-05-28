from requests import RequestException

from exceptions import ParserFindTagException
from bs4 import BeautifulSoup


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        RequestException(
            f'Возникла ошибка при загрузке страницы {url}'
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        raise ParserFindTagException(error_msg)
    return searched_tag


def get_request(url, session):
    response = get_response(session, url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    return soup