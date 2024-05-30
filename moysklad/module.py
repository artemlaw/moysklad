import logging
import requests
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MoySklad')


def handle_request(max_retries=3, delay_seconds=15):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    response = func(*args, **kwargs)
                    response.raise_for_status()
                    return response
                except requests.RequestException as e:
                    logger.error(f'Неудачный запрос, ошибка: {e}. Повтор через {delay_seconds} секунд.')
                    time.sleep(delay_seconds)
            logger.error(f'Достигнуто максимальное количество попыток ({max_retries}). Прекращение повторных запросов.')
            return None
        return wrapper
    return decorator


class MoySklad:
    def __init__(self, api_key: str):
        self.headers = {'Accept-Encoding': 'gzip', 'Authorization': api_key, 'Content-Type': 'application/json'}
        self.host = 'https://api.moysklad.ru/api/remap/1.2/'

    @handle_request()
    def get_data(self, url, params=None):
        return requests.get(url, headers=self.headers, params=params)

    @handle_request()
    def post_data(self, url, data):
        return requests.post(url, headers=self.headers, json=data)

    @handle_request()
    def put_data(self, url, data):
        return requests.put(url, headers=self.headers, json=data)

    @handle_request()
    def delete_data(self, url):
        return requests.delete(url, headers=self.headers)

    def fetch_data(self, url, params):
        items = []
        while True:
            result = self.get_data(url, params)
            if result:
                response_json = result.json()
                items += response_json.get('rows', [])
                params['offset'] += params['limit']
                if response_json.get('meta', {}).get('size', 0) < params['offset']:
                    break
            else:
                break
        return items

    def get_products_list(self):
        url = f'{self.host}entity/product'
        params = {'limit': 1000, 'offset': 0}
        return self.fetch_data(url, params)

    def update_product(self, product):
        url = f'{self.host}entity/product/{product.get("id")}'

        result = self.put_data(url, data=product)

        if result:
            response_json = result.json()
        else:
            response_json = []
            logger.error('Не удалось обновить номенклатуру.')
        return response_json

    def get_bundles(self):
        url = f'{self.host}entity/bundle?expand=components.rows.assortment'
        params = {'limit': 100, 'offset': 0}
        return self.fetch_data(url, params)

    def update_bundle(self, bundle):
        url = f'{self.host}entity/bundle/{bundle.get("id")}'
        result = self.put_data(url, data=bundle)

        if result:
            response_json = result.json()
        else:
            response_json = []
            print('Не удалось обновить номенклатуру.')
        return response_json

    def get_product_label(self, product, count=1):
        url = f'{self.host}entity/product/{product.get("id")}/export/'
        data = {
            "organization": {
                "meta": {
                    "href": "https://api.moysklad.ru/api/remap/1.2/entity/organization/"
                            "29310743-0c62-11ef-0a80-1736000feae2",
                    "metadataHref": "https://api.moysklad.ru/api/remap/1.2/entity/organization/metadata",
                    "type": "organization",
                    "mediaType": "application/json",
                    "uuidHref": "https://online.moysklad.ru/app/#mycompany/edit?id=29310743-0c62-11ef-0a80-1736000feae2"
                }
            },
            "count": count,
            "salePrice": {
              "priceType": {
                "meta": {
                  "href": "https://api.moysklad.ru/api/remap/1.2/context/companysettings/pricetype/"
                          "2933628a-0c62-11ef-0a80-1736000feaeb",
                  "type": "pricetype",
                  "mediaType": "application/json"
                }
              }
            },
            "template": {
              "meta": {
                "href": "https://api.moysklad.ru/api/remap/1.2/entity/assortment/metadata/customtemplate/"
                        "d01825c6-7377-415b-8db4-f99b8dbd1fb4",
                "type": "embeddedtemplate",
                "mediaType": "application/json"
              }
            }
        }
        result = self.post_data(url, data=data)
        if result:
            response_content = result.content
        else:
            response_content = None
            logger.error('Не удалось создать заказ.')
        return response_content

    def get_stock_all(self):
        url = f'{self.host}report/stock/all'
        params = {'limit': 1000, 'offset': 0}
        stocks_list = []

        while True:
            result = self.get_data(url, params)
            if result:
                response_json = result.json()
                stocks_list += response_json.get('rows')
                params['offset'] += params['limit']
                if response_json.get('meta').get('size') < params['offset']:
                    break
            else:
                break
        logger.info(f'Получен остаток по номенклатуре: {len(stocks_list)}')
        return stocks_list

    def get_orders(self, filter_str):
        # Пример:
        # from_date_f = f'{from_date} 00:00:00.000'
        # to_date_f = f'{to_date} 23:59:00.000'
        # filter_str = f'?filter=moment>{from_date};moment<{to_date};&order=name,desc&expand=positions.assortment,state'
        url = f'{self.host}entity/customerorder{filter_str}'
        params = {'limit': 100, 'offset': 0}
        orders_list = []
        while True:
            result = self.get_data(url, params)
            if result:
                response_json = result.json()
                orders_list += response_json.get('rows')
                params['offset'] += params['limit']
                if response_json.get('meta').get('size') < params['offset']:
                    break
            else:
                break
        logger.info(f'Получено заказов за период: {len(orders_list)}')
        return orders_list


if __name__ == '__main__':
    MS_API_TOKEN = '**************'
    ms = MoySklad(MS_API_TOKEN)
    products = ms.get_products_list()
    print(products[0])
