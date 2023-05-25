import re
from urllib.parse import urljoin
import logging
from collections import defaultdict

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from utils import get_response, find_tag
from outputs import control_output
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL, EXPECTED_STATUS
from configs import configure_argument_parser, configure_logging


def whats_new(session):
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор'), ]
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    session = requests_cache.CachedSession()
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(
        soup,
        'section',
        attrs={'id': 'what-s-new-in-python'}
    )
    div_with_ul = find_tag(
        main_div,
        'div',
        attrs={'class': 'toctree-wrapper'}
    )
    sections_by_python = div_with_ul.find_all(
        'li',
        attrs={'class': 'toctree-l1'}
    )
    print(sections_by_python[0].prettify())

    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )
    return results


def latest_versions(session):
    results = [('Ссылка на документацию', 'Версия', 'Статус'), ]
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise Exception('Не найден список c версиями Python')

    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    session = requests_cache.CachedSession()
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_tag = find_tag(soup, 'div', {'role': 'main'})
    table_tag = find_tag(main_tag, 'table', {'class': 'docutils'})
    pdf_a4_tag = find_tag(table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = find_tag(soup, 'section', {'id': 'numerical-index'})
    pep_row = main_tag.find_all('tr')
    count_status_in_card = defaultdict(int)
    result = [('Статус', 'Количество')]
    for i in range(1, len(pep_row)):
        href_tag = pep_row[i].a['href']
        pep_link = urljoin(PEP_URL, href_tag)
        response = get_response(session, pep_link)
        soup = BeautifulSoup(response.text, 'lxml')
        main_card_tag = find_tag(soup, 'section', {'id': 'pep-content'})
        main_card_dl_tag = find_tag(
            main_card_tag,
            'dl',
            {
                'class': 'rfc2822 field-list simple'
            }
        )
        for tag in main_card_dl_tag:
            if tag.name == 'dt' and tag.text == 'Status:':
                status = tag.next_sibling.next_sibling.string
                count_status_in_card[status] = count_status_in_card.get(
                    status, 0
                ) + 1
                if len(pep_row[i].td.text) != 1:
                    table_status = pep_row[i].td.text[1:]
                    if status[0] != table_status:
                        logging.info(
                            '\n'
                            'Несовпадающие статусы:\n'
                            f'{pep_link}\n'
                            f'Статус в карточке: {status}\n'
                            f'Ожидаемые статусы: '
                            f'{EXPECTED_STATUS[table_status]}\n'
                        )
    for key in count_status_in_card:
        result.append((key, str(count_status_in_card[key])))
    result.append(('Total', len(peps_row)-1))
    return result


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()

    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    
    # Если из функции вернулись какие-то результаты,
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.') 

if __name__ == '__main__':
    main()