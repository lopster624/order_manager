import datetime
import requests
import xml.etree.ElementTree as ET

from celery import shared_task
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

import orders.models as models
from order_manager.settings import SPREADSHEET_ID, GOOGLE_AUTH_FILE_PATH, GOOGLE_API_SCOPES


def get_current_dollar_rate():
    """Получить текущий курс доллара."""
    response = requests.get('https://www.cbr.ru/scripts/XML_daily.asp')
    root = ET.fromstring(response.content)
    return float(root.find(".//*[@ID='R01235']/Value").text.replace(',', '.'))


def get_dollar_rate():
    """
    Получить курс доллара.
    Если курс доллара за сегодня уже сохранен - получить его.
    Если нет - получить новый курс доллара и сохранить.
    """
    from django.utils import timezone
    today = timezone.now().date()
    dollar_rate = models.DollarRate.objects.filter(date=today).first()
    if dollar_rate:
        return dollar_rate.rate
    new_dollar_rate = get_current_dollar_rate()
    models.DollarRate.objects.create(date=today, rate=new_dollar_rate)
    return new_dollar_rate


def convert_dollar_2_rubble(value):
    """Перевести доллары в рубли по текущему курсу."""
    return value * get_dollar_rate()


def get_modified_time(file_id=SPREADSHEET_ID):
    """Получить данные последнего изменения файла."""
    service2 = build('drive', 'v3', credentials=get_credentials())
    results = service2.files().get(fileId=file_id,
                                   fields="modifiedTime").execute()
    modified_time = results.get('modifiedTime', None)
    if modified_time:
        return parse_datetime(modified_time)


def get_credentials():
    """Получить токен для аутентификации в сервисах google."""
    return service_account.Credentials.from_service_account_file(
        GOOGLE_AUTH_FILE_PATH, scopes=GOOGLE_API_SCOPES)


def get_database_data():
    """Получить данные из google sheet."""
    SAMPLE_RANGE_NAME = 'A2:AA1000'

    service = build('sheets', 'v4', credentials=get_credentials())
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])
    return values


def delete_orders(orders_id):
    """
    Удалить список заказов по id.
    :param orders_id: сет id заказов на удаление.
    :return: количество удаленных заказов.
    """
    return models.Order.objects.filter(id__in=orders_id).delete()[0]


def create_orders(orders_id, orders):
    """
    Создать заказы.
    :param orders_id: сет id заказов, которые необходимо создать.
    :param orders: список списков с данными всех заказов из таблицы.
    :return: количество созданных заказов.
    """
    dollar_rate = get_dollar_rate()
    objects = []
    for order in orders:
        if order[0] in orders_id:
            objects.append(
                models.Order(id=order[0],
                             number=order[1],
                             dollar_cost=order[2],
                             ruble_cost=order[2] * dollar_rate,
                             delivery_time=order[3])
            )
    return len(models.Order.objects.bulk_create(objects, batch_size=100))


def update_orders(db_orders_ids, data):
    """
    Обновить заказы в базе данных данными из data.
    :param db_orders_ids: все id заказов из базы данных.
    :param data: Список заказов. Заказ - список с атрибутами [id, number, dollar_cost, delivery_time]
    :return: количество измененных заказов.
    """
    dollar_rate = get_dollar_rate()
    db_orders = models.Order.objects.all()
    orders_on_update = {order[0]: order[1:] for order in data if order[0] in db_orders_ids}
    update_in_bulk = []
    updated = 0
    for order in db_orders:
        new_order = orders_on_update.get(order.id, None)
        if not new_order or order.id not in orders_on_update:
            continue
        updated_fields = (order.number != new_order[0],
                          order.dollar_cost != new_order[1],
                          order.delivery_time != new_order[2])
        if any(updated_fields):
            updated += 1
            if updated_fields[0]:
                order.number = new_order[0]
            if updated_fields[1]:
                order.dollar_cost = new_order[1]
                order.ruble_cost = dollar_rate * new_order[1]
            if updated_fields[2]:
                order.delivery_time = new_order[2]
            update_in_bulk.append(order)
    models.Order.objects.bulk_update(update_in_bulk,
                                     fields=['number', 'ruble_cost', 'dollar_cost', 'delivery_time'],
                                     batch_size=100),
    return updated


def check_update_time_decorator():
    """
    Проверить, что данные в таблице были изменены.
    Вернуть False - если изменены.
    True - если не изменены. Также обновить данные о последней синхронизации.
    """

    modified_time = get_modified_time()
    db_info = models.UpdateTableInfo.objects.first()
    if modified_time and db_info:
        if modified_time < db_info.last_update:
            print("Файл не был изменен.")
            return False

    if db_info:
        db_info.last_update = timezone.now()
        db_info.save()
    else:
        models.UpdateTableInfo.objects.create(last_update=timezone.now())
    return True


@shared_task
def refresh_data():
    """Обновить все данные в базе данных о заказах."""
    if not check_update_time_decorator():
        return
    data = list(map(lambda x: [int(x[0]), int(x[1]), int(x[2]), datetime.datetime.strptime(x[3], "%d.%m.%Y").date()],
                    get_database_data()))

    orders_ids = {row[0] for row in data}
    db_orders_ids = set(models.Order.objects.all().values_list('id', flat=True))

    deleted = delete_orders(db_orders_ids - orders_ids)
    print(f'Удалено {deleted} заказов.')

    updated = update_orders(db_orders_ids, data)
    print(f'Обновлено {updated} заказов.')

    created = create_orders(orders_ids - db_orders_ids, data)
    print(f'Создано {created} заказов.')
