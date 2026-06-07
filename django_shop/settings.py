"""
Django settings for django_shop project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', True)

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-me'
    else:
        raise RuntimeError('SECRET_KEY must be set when DEBUG=False.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

_admin_url_segment = os.getenv('ADMIN_URL_PATH', 'admin').strip().strip('/')
if not _admin_url_segment:
    _admin_url_segment = 'admin'
ADMIN_URL_PATH = f'{_admin_url_segment}/'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'tinymce',
    
    # Local apps
    'shop',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРµСЂРµРґ CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_shop.middleware.MediaEmbedHeadersMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'django_shop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_shop.wsgi.application'


# Database
# Parse DATABASE_URL from environment
database_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/dbname')
url = urlparse(database_url)

if url.scheme == "sqlite":
    sqlite_name = url.path if url.path else "/db.sqlite3"
    if sqlite_name.startswith("/") and len(sqlite_name) >= 3 and sqlite_name[2] == ":":
        sqlite_name = sqlite_name[1:]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_name,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],  # Remove leading slash
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv('STATIC_URL', '/django-static/')
STATIC_ROOT = Path(os.getenv('STATIC_ROOT', BASE_DIR / 'staticfiles'))

# Media files
MEDIA_URL = os.getenv('MEDIA_URL', '/static/')  # РЎРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ СЃ FastAPI
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', BASE_DIR / 'media'))

# Ensure media directory exists
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', DEBUG and not CORS_ALLOWED_ORIGINS)
CORS_ALLOW_CREDENTIALS = True

SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# drf-spectacular settings for Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Бэкенд магазина Novotech',
    'DESCRIPTION': (
        'REST API интернет-магазина: бренды, группы, товары, характеристики, '
        'медиа-файлы, новости, поиск, каталог, заявки и заказы.\n\n'
        'Администрирование ведется через Django admin. Все ответы - JSON.'
    ),
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'API Maintainer',
        'url': 'https://example.com',
        'email': 'admin@example.com',
    },
    'LICENSE': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT',
    },
    'TAGS': [
        {'name': 'brands', 'description': 'Бренды товаров'},
        {'name': 'groups', 'description': 'Группы, категории и дерево категорий'},
        {'name': 'products', 'description': 'Товары: CRUD и фильтрация'},
        {'name': 'attributes', 'description': 'Характеристики и значения товара'},
        {'name': 'media', 'description': 'Медиа-файлы товаров'},
        {'name': 'orders', 'description': 'Заказы и заявки'},
        {'name': 'news', 'description': 'Новости магазина'},
        {'name': 'agents', 'description': 'Менеджеры и консультанты'},
        {'name': 'filters', 'description': 'Фильтры каталога'},
    ],
}

# Custom settings
FRAME_ANCESTOR_ORIGINS = os.getenv('FRAME_ANCESTOR_ORIGINS', '*' if DEBUG else "'self'")

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 25))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@localhost')

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CATALOG_IMPORT_QUEUE_NAME = os.getenv('CATALOG_IMPORT_QUEUE_NAME', 'catalog_import_jobs')
CATALOG_IMPORT_QUEUE_BLOCK_SECONDS = int(os.getenv('CATALOG_IMPORT_QUEUE_BLOCK_SECONDS', '5'))

TINYMCE_DEFAULT_CONFIG = {
    'height': 420,
    'menubar': True,
    'plugins': (
        'advlist autolink lists link image charmap preview anchor '
        'searchreplace visualblocks code fullscreen insertdatetime media table importcss '
        'wordcount help quickbars'
    ),
    'toolbar': (
        'undo redo | blocks styles | bold italic underline | '
        'alignleft aligncenter alignright alignjustify | '
        'bullist numlist outdent indent | link image media table | '
        'removeformat code preview'
    ),
    'content_css': ['/django-static/shop/css/tinymce-content.css'],
    'style_formats_merge': False,
    'style_formats': [],
    'table_class_list': [],
    'table_default_attributes': {},
    'table_sizing_mode': 'relative',
    'table_border_styles': [
        {'title': 'Таблица каталога', 'value': 'var(--catalog-table-border-style)'},
        {'title': 'Сплошной', 'value': 'solid'},
        {'title': 'Точками', 'value': 'dotted'},
        {'title': 'Черточками', 'value': 'dashed'},
        {'title': 'Двойной', 'value': 'double'},
        {'title': 'Паз', 'value': 'groove'},
        {'title': 'Шип', 'value': 'ridge'},
        {'title': 'Вставка', 'value': 'inset'},
        {'title': 'Вырезка', 'value': 'outset'},
        {'title': 'Нет', 'value': 'none'},
        {'title': 'Скрытый', 'value': 'hidden'},
    ],
    'table_toolbar': (
        'tableprops tabledelete | '
        'tableinsertrowbefore tableinsertrowafter tabledeleterow | '
        'tableinsertcolbefore tableinsertcolafter tabledeletecol'
    ),
    'table_appearance_options': True,
    'table_advtab': True,
    'table_cell_advtab': True,
    'table_row_advtab': True,
    'branding': False,
    'promotion': False,
}
