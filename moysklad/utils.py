import requests
import fitz  # PyMuPDF pip install pymupdf
import importlib.resources as pkg_resources
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO

from moysklad.module import MoySklad


def get_value_by_name(data, target_name):
    return next((item.get('value') for item in data if item.get('name') == target_name), None)


def get_filter_name(order_str):
    name_list = [name.strip() for name in order_str.split(',') if name.strip()]
    return ';'.join(f'name={name}' for name in name_list) + ';'


def create_custom_page(orders_count, p_name):
    packet = BytesIO()
    width, height = 58 * mm, 40 * mm
    can = canvas.Canvas(packet, pagesize=(width, height))
    with pkg_resources.path('moysklad', 'Roboto-Bold.ttf') as font_path:
        pdfmetrics.registerFont(TTFont('Roboto-Bold', str(font_path)))
    font_size = 8
    can.setFont('Roboto-Bold', font_size)
    line1 = f'по 1 товару в заказе ({orders_count}шт. заказов)'
    line2 = f'1 шт - {p_name}'
    max_width = width - 20
    y = height - 20
    lines1 = simpleSplit(line1, 'Roboto-Bold', font_size, max_width)
    for line in lines1:
        can.drawString(10, y, line)
        y -= (font_size + 2)

    lines2 = simpleSplit(line2, 'Roboto-Bold', font_size, max_width)
    y -= (font_size + 2)
    for line in lines2:
        can.drawString(10, y, line)
        y -= (font_size + 2)
    can.save()
    packet.seek(0)
    custom_pdf = fitz.open(stream=packet.read(), filetype="pdf")
    return custom_pdf


def get_product_info(order):
    product_ = order.get('positions', {}).get('rows', [])[0].get('assortment', {})
    product_name = product_.get('name', '')
    product_id = product_.get('id', '')
    label_wb_link = get_value_by_name(order.get('attributes', []), 'Ссылка на этикетку')
    res = requests.get(label_wb_link, headers={'Content-Type': 'application/json'})
    if res.status_code == 200:
        label_wb_pdf = res.content
    else:
        print(f'Не удалось получить этикетку по заказу: {order.get("name")}')
        label_wb_pdf = None
    return product_name, product_id, label_wb_pdf


def create_combined_pdf(ms_client, orders):
    combined_pdf = fitz.open()
    dict_ = {}

    for order in orders:
        product_name, product_id, label_wb_pdf = get_product_info(order)
        if product_name:
            if product_name not in dict_:
                dict_[product_name] = {'id': product_id, 'orders': []}
            dict_[product_name]['orders'].append({'order_name': order.get('name', ''), 'label': label_wb_pdf})

    result_list = sorted(dict_.keys())

    for product_name in result_list:
        product = dict_[product_name]
        orders_list = product.get('orders', [])
        label_first = create_custom_page(orders_count=len(orders_list), p_name=product_name)
        combined_pdf.insert_pdf(label_first)

        for order_ in orders_list:
            label_wb = order_.get('label')
            if label_wb:
                label_wb_reader = fitz.open(stream=BytesIO(label_wb), filetype="pdf")
                label_reader = fitz.open(stream=BytesIO(ms_client.get_label(product.get('id'))), filetype="pdf")
                combined_pdf.insert_pdf(label_wb_reader, from_page=0, to_page=0)
                combined_pdf.insert_pdf(label_reader, from_page=0, to_page=0)

    return combined_pdf


if __name__ == '__main__':
    MS_API_TOKEN = '******'
    ms = MoySklad(MS_API_TOKEN)
    orders_names = "1758748584, 1758676139,1757202294,  1757196839,1758620190, ,,"
    filter_name = get_filter_name(orders_names)
    filters = f'?filter={filter_name}&order=name,desc&expand=positions.assortment,state'
    ms_orders = ms.get_orders(filters)
    # Используйте функцию create_combined_pdf для создания объединенного PDF-файла
    overdue_orders_pdf = create_combined_pdf(ms_client=ms, orders=ms_orders)
    overdue_orders_pdf.save("overdue_orders.pdf")
    print("PDF файлы успешно сохранены в overdue_orders.pdf")
