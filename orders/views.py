from django.db.models import Sum
from django.shortcuts import render

from orders.models import Order
from orders.utils import refresh_data


def get_orders_info(request):
    """Обновить информацию в БД и вернуть информацию о заказах."""
    refresh_data.delay()
    context = {'orders': Order.objects.order_by('id')[:10],
               'dates': Order.objects.order_by('id').values_list('delivery_time', flat=True),
               'total_price':  Order.objects.aggregate(Sum('dollar_cost'))['dollar_cost__sum']
               }
    return render(request, 'orders.html', context=context)
