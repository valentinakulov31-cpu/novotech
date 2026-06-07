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

PostgreSQL используется системная, не в Docker.

Docker поднимает:

- Django/Gunicorn на `127.0.0.1:8000`;
- Redis на `127.0.0.1:6379` для фонового импорта каталога;
- отдельный worker импорта `novotech_import_worker`, который читает задания из Redis;
- публичный ingress через Caddy на `80/443`;
- watchdog-контейнер `autoheal`, который перезапускает ingress при провале его собственного healthcheck.

Frontend живет отдельным проектом и должен быть доступен на `127.0.0.1:3000`. Публичный вход на домен держит только контейнер `novotech_ingress`. Путь к Django admin задается через `ADMIN_URL_PATH` в `.env` и в проде не должен оставаться равным `/admin/`.

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
ADMIN_URL_PATH=replace-with-secret-admin-path

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
REDIS_URL=redis://127.0.0.1:6379/0
CATALOG_IMPORT_QUEUE_NAME=catalog_import_jobs
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
docker compose logs -f import_worker
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
http://2.26.104.125:8000/$ADMIN_URL_PATH/
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

## 6. Публичный ingress через Docker

Публичный вход не должен зависеть от системного `nginx` на хосте. Вместо этого проект поднимает контейнер `novotech_ingress` с Caddy, который:

- слушает `80/443`;
- использует уже выпущенный TLS-сертификат для `nvt24.ru`;
- отправляет `/` на frontend `127.0.0.1:3000`;
- отправляет скрытый admin path `/$ADMIN_URL_PATH/`, а также `/tinymce` и `/v1` на Django `127.0.0.1:8000`;
- отдает `/django-static/*` и `/static/*` напрямую из смонтированных директорий.

Текущий рабочий вариант TLS использует уже выпущенный Let's Encrypt сертификат из `/etc/letsencrypt/live/nvt24.ru/`, а Caddy читает его в контейнере. Старый `/admin/` снаружи должен отвечать `404`.

После появления домена и HTTPS в `.env` должны быть такие настройки:

```env
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
ADMIN_URL_PATH=replace-with-secret-admin-path
CORS_ALLOW_ALL_ORIGINS=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

### Отключение системного `nginx`

Если раньше домен обслуживал host-level `nginx`, его нужно убрать из цепочки, чтобы владелец `80/443` был один:

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

### Запуск ingress

```bash
cd /root/project_shop/novotech
docker compose build ingress
docker compose up -d ingress autoheal
```

### Автопродление сертификата

`certbot.timer` на хосте должен оставаться включенным, но renewal нужно делать не через `nginx`-plugin, а через `standalone` с hook-скриптами:

- `docker/caddy/hooks/pre-renew.sh` освобождает `80/443`, останавливая только `novotech_ingress`;
- `docker/caddy/hooks/post-renew.sh` поднимает ingress обратно после challenge.

После смены схемы обновления сертификатов обязательно проверить:

```bash
certbot renew --dry-run
```

Проверить:

```bash
docker compose ps
docker compose logs --tail=100 ingress
curl -k -I --resolve nvt24.ru:443:127.0.0.1 https://nvt24.ru/
curl -I -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/v1/healthz/
ss -ltnp | grep -E ':80|:443|:3000|:8000'
```

## 7. Импорт XLSX и файлы

Импорт XLSX теперь выполняется в фоне:

- админка создаёт задание `Импорт каталога`;
- XLSX сохраняется в `MEDIA_ROOT/import_jobs/...`;
- web-контейнер только ставит задание в Redis;
- `novotech_import_worker` обрабатывает импорт отдельно и пишет статус/ошибки в БД.

Для проверки очереди и worker:

```bash
docker compose ps
docker compose logs --tail=100 import_worker
docker compose exec web python manage.py process_import_jobs --once
```

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
docker compose logs --tail=100 ingress
docker compose exec web python manage.py check
curl -i http://127.0.0.1:8000/v1/healthz/
```

Как отличить тип падения:

- нет `80/443`, но `3000` и `8000` живы: проблема в ingress;
- `8000` не отвечает: проблема в backend;
- `3000` не отвечает: проблема во frontend;
- `ingress` в статусе `unhealthy`: `autoheal` должен перезапустить именно публичный ingress, не трогая backend и frontend.
