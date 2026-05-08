# Деплой Novotech

Проект на сервере лежит как есть, без дополнительной папки `app`:

```text
/root/project_shop/novotech/
  django_shop/
  docker/
  shop/
  Dockerfile
  docker-compose.yml
  manage.py
  requirements.txt
  .env
```

PostgreSQL используется системная, не в Docker. Docker поднимает только Django/Gunicorn.

## 1. PostgreSQL

Если база уже создана, этот шаг можно пропустить.

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE django_shop;
CREATE USER django_shop_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
ALTER ROLE django_shop_user SET client_encoding TO 'utf8';
ALTER ROLE django_shop_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE django_shop_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE django_shop TO django_shop_user;

\c django_shop

CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO django_shop_user;

\q
```

Проверка подключения:

```bash
psql "postgresql://django_shop_user:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/django_shop" -c "SELECT current_database(), current_user;"
```

## 2. `.env` для запуска по IP без HTTPS

Пока домена и HTTPS нет, используй такие настройки:

```env
DEBUG=True
SECRET_KEY=change-me-with-python-secrets-token-urlsafe-64

DATABASE_URL=postgresql://django_shop_user:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/django_shop

ALLOWED_HOSTS=2.26.104.125,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://2.26.104.125:8000
CORS_ALLOWED_ORIGINS=http://2.26.104.125:8000
CORS_ALLOW_ALL_ORIGINS=True

MEDIA_URL=/static/
STATIC_URL=/django-static/

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False

FRAME_ANCESTOR_ORIGINS='self'

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=your-gmail@gmail.com

RUN_MIGRATIONS=1
RUN_COLLECTSTATIC=1
```

Редактирование:

```bash
cd /root/project_shop/novotech
nano .env
```

## 3. Docker-запуск

Подготовить папки для статики и загруженных файлов:

```bash
sudo mkdir -p /var/www/django_shop/staticfiles /var/www/django_shop/media
sudo chmod -R 777 /var/www/django_shop
```

Собрать и запустить:

```bash
cd /root/project_shop/novotech
docker compose build --no-cache
docker compose up -d --force-recreate
docker compose logs -f web
```

Проверка:

```bash
curl -i http://127.0.0.1:8000/v1/healthz/
curl -i http://127.0.0.1:8000/v1/docs/
```

В браузере:

```text
http://2.26.104.125:8000/v1/healthz/
http://2.26.104.125:8000/v1/docs/
http://2.26.104.125:8000/admin/
```

Создать админа:

```bash
docker compose exec web python manage.py createsuperuser
```

## 4. Если `.env` изменился

`docker compose restart` не всегда пересоздает контейнер с новым env. После правки `.env` делай так:

```bash
docker compose down
docker compose up -d --force-recreate
```

Проверить env внутри контейнера:

```bash
docker compose exec web env | grep -E "DEBUG|ALLOWED_HOSTS|CSRF|CORS|SECURE|DATABASE_URL"
```

## 5. Обновление кода

```bash
cd /root/project_shop/novotech
git pull
docker compose build --no-cache
docker compose up -d --force-recreate
docker compose logs -f web
```

Если Git не используется, заменить файлы проекта вручную и выполнить те же команды `build` и `up`.

## 6. Nginx, когда будет нужен нормальный доступ

Пример конфига:

```nginx
server {
    listen 80;
    server_name 2.26.104.125;

    client_max_body_size 100m;

    location /django-static/ {
        alias /var/www/django_shop/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /static/ {
        alias /var/www/django_shop/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

После появления домена и HTTPS в `.env` вернуть:

```env
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOW_ALL_ORIGINS=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

## 7. Импорт XLSX и файлы

В колонках `media_urls`, `gallery_urls`, `document_urls`, `certificate_urls` можно указывать:

- URL, например `https://example.com/file.pdf`;
- уже готовые `/static/...` ссылки;
- локальные пути на сервере, например `/tmp/import/product-1.jpg`.

Важно: локальный путь должен существовать именно на сервере, где работает контейнер. Если файл лежит на компьютере администратора, сначала загрузи его на сервер, потом укажи серверный путь в XLSX.

Несколько файлов в одной ячейке можно разделять запятыми, точками с запятой или переносами строк.

## 8. Диагностика

```bash
docker compose ps
docker compose logs --tail=100 web
docker compose exec web python manage.py check
curl -i http://127.0.0.1:8000/v1/healthz/
```
