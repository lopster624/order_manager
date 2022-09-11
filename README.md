# order_manager

Сервис для просмотра заказов. 
Сервис автоматически проверяет в файле google sheet изменения в существующих заказах и обновляет заказы
в базе данных, считая цену в рублях по текущему курсу ЦБ. 



## Зависимости

Сервис работает на Python 3.8 и Django 3.2.15.
Все прочие зависимости вы можете найти в файле requirements.txt.

## Установка и запуск

### 1) Установка зависимостей из requirements.txt.
Python должен быть уже установлен.
```shell
pip install -r requirements.txt
```

### 2) Установка docker и запуск в нем Redis.
Докер нужно установить самому :)
```shell
docker run -p 6379:6379 --name some-redis -d redis
```

### 3) Установка Postgres.
Можно установить как на компьютер, так и развернуть в docker.

### 4) Запуск сервиса.

```shell
python manage.py runserver
```

### 5) Запуск worker celery.
```shell
celery -A order_manager worker -l info -P solo
```



### 6) Запуск планировщика задач celery 
Данный компонент необходим для автоматического запуска задач.
```shell
celery -A order_manager beat -l info
```


## Веб-интерфейс

Просмотр существующих заявок можно осуществить по [ссылке](http://127.0.0.1:8000/orders/). 