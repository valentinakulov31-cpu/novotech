# Production deployment

Инструкция рассчитана на Ubuntu 22.04/24.04, PostgreSQL, Gunicorn и Nginx.

## Docker variant with system PostgreSQL

В проект добавлены:

- `Dockerfile` - образ Django/Gunicorn.
- `docker/entrypoint.sh` - запускает `migrate` и `collectstatic`, потом Gunicorn.
- `docker-compose.yml` - поднимает только Django-контейнер. PostgreSQL остается системной.
- `docker.env.example` - пример env для Docker-запуска.

PostgreSQL должен быть установлен на хосте, не в Docker. Так как `docker-compose.yml` использует `network_mode: host`, контейнер видит системную PostgreSQL по `127.0.0.1:5432`.

Установить Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Подготовить директории для файлов:

```bash
sudo mkdir -p /var/www/django_shop/media /var/www/django_shop/staticfiles
sudo chown -R 1000:1000 /var/www/django_shop
```

Создать `.env`:

```bash
cp docker.env.example .env
nano .env
```

Обязательные значения:

```env
DEBUG=False
SECRET_KEY=<long-random-secret>
DATABASE_URL=postgresql://django_shop_user:<password>@127.0.0.1:5432/django_shop
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
```

Системную PostgreSQL подготовить так же, как в разделе PostgreSQL ниже. База, пользователь и пароль должны совпадать с `DATABASE_URL`.

Собрать и запустить:

```bash
docker compose build
docker compose up -d
docker compose logs -f web
```

Создать админа:

```bash
docker compose exec web python manage.py createsuperuser
```

Nginx при Docker-варианте проксирует на Gunicorn в host network:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Статику и media оставить как в Nginx-конфиге ниже:

```nginx
location /django-static/ {
    alias /var/www/django_shop/staticfiles/;
}

location /static/ {
    alias /var/www/django_shop/media/;
}
```

Обновление Docker-релиза:

```bash
git pull
docker compose build
docker compose up -d
docker compose logs -f web
```

## 1. Подготовить сервер

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx git
```

Создать пользователя для приложения:

```bash
sudo adduser --system --group --home /opt/django_shop django_shop
sudo mkdir -p /var/www/django_shop/media /var/www/django_shop/staticfiles
sudo chown -R django_shop:django_shop /opt/django_shop /var/www/django_shop
```

## 2. Развернуть код

Скопировать проект в `/opt/django_shop/app`. Например:

```bash
sudo -u django_shop mkdir -p /opt/django_shop/app
sudo -u django_shop git clone <REPO_URL> /opt/django_shop/app
```

Если код загружается архивом, распаковать его в ту же папку так, чтобы рядом лежали `manage.py`, `requirements.txt`, `django_shop/`, `shop/`.

Создать окружение:

```bash
cd /opt/django_shop/app
sudo -u django_shop python3 -m venv .venv
sudo -u django_shop .venv/bin/pip install --upgrade pip
sudo -u django_shop .venv/bin/pip install -r requirements.txt
```

## 3. PostgreSQL

Зайти в PostgreSQL:

```bash
sudo -u postgres psql
```

Создать базу, пользователя и расширение:

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

Пароль из SQL должен совпадать с `DATABASE_URL` в `.env`.

## 4. Заполнить `.env`

Создать файл:

```bash
cd /opt/django_shop/app
sudo -u django_shop cp .env.example .env
sudo -u django_shop nano .env
```

Минимальный продовый пример:

```env
DEBUG=False
SECRET_KEY=PASTE_GENERATED_SECRET_KEY_HERE

DATABASE_URL=postgresql://django_shop_user:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/django_shop

ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com

MEDIA_URL=/static/
MEDIA_ROOT=/var/www/django_shop/media
STATIC_URL=/django-static/
STATIC_ROOT=/var/www/django_shop/staticfiles

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=False

FRAME_ANCESTOR_ORIGINS='self'

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=no-reply@example.com
EMAIL_HOST_PASSWORD=CHANGE_ME_SMTP_PASSWORD
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=no-reply@example.com
```

Сгенерировать `SECRET_KEY`:

```bash
python3 - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Если сайт пока без HTTPS, временно поставить `SECURE_SSL_REDIRECT=False`, `SESSION_COOKIE_SECURE=False`, `CSRF_COOKIE_SECURE=False`, `SECURE_HSTS_SECONDS=0`. После выпуска сертификата вернуть значения из примера.

## 5. Миграции, статика, админ

```bash
cd /opt/django_shop/app
sudo -u django_shop .venv/bin/python manage.py check --deploy
sudo -u django_shop .venv/bin/python manage.py migrate
sudo -u django_shop .venv/bin/python manage.py collectstatic --noinput
sudo -u django_shop .venv/bin/python manage.py createsuperuser
```

## 6. Gunicorn systemd service

Создать `/etc/systemd/system/django-shop.service`:

```ini
[Unit]
Description=Django Shop Gunicorn
After=network.target postgresql.service

[Service]
User=django_shop
Group=django_shop
WorkingDirectory=/opt/django_shop/app
EnvironmentFile=/opt/django_shop/app/.env
ExecStart=/opt/django_shop/app/.venv/bin/gunicorn django_shop.wsgi:application \
  --bind 127.0.0.1:8001 \
  --workers 3 \
  --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now django-shop
sudo systemctl status django-shop
```

Логи:

```bash
sudo journalctl -u django-shop -f
```

## 7. Nginx

Создать `/etc/nginx/sites-available/django-shop`:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

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
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включить сайт:

```bash
sudo ln -s /etc/nginx/sites-available/django-shop /etc/nginx/sites-enabled/django-shop
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```

После успешного сертификата проверить `.env`, чтобы SSL-настройки были включены:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

Затем:

```bash
sudo systemctl restart django-shop
```

## 9. Импорт XLSX и локальные файлы

Импорт поддерживает URL и локальные пути в колонках `media_urls`, `gallery_urls`, `document_urls`, `certificate_urls`.

Важный момент: локальный путь читается на сервере, где работает Django. Если файл лежит на компьютере администратора, его сначала нужно загрузить на сервер, например в `/tmp/import_files/`, и уже этот серверный путь указать в XLSX.

Пример:

```text
/tmp/import_files/product-1.jpg
https://example.com/manual.pdf
/var/import/certificates/cert-1.pdf
```

Несколько файлов в одной ячейке можно разделять запятыми, точками с запятой или переносами строк. При импорте локальные файлы копируются в `/var/www/django_shop/media/admin_uploads/...`, а в базе сохраняется `/static/admin_uploads/...`.

## 10. Обновление релиза

```bash
cd /opt/django_shop/app
sudo -u django_shop git pull
sudo -u django_shop .venv/bin/pip install -r requirements.txt
sudo -u django_shop .venv/bin/python manage.py migrate
sudo -u django_shop .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart django-shop
sudo systemctl status django-shop
```

## 11. Быстрая диагностика

```bash
sudo systemctl status django-shop
sudo journalctl -u django-shop -n 100 --no-pager
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
curl -I http://127.0.0.1:8001/v1/healthz/
curl -I https://example.com/v1/healthz/
```
