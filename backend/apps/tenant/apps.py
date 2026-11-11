from django.apps import AppConfig
from django.db.backends.base.base import NO_DB_ALIAS
from django.db.backends.signals import connection_created


def ensure_schema(sender, connection, **kwargs):
    """Create this app's Postgres schema on connect so migrations always have a home."""
    # Skip the maintenance connection Django opens to create/drop test databases.
    if connection.vendor != 'postgresql' or connection.alias == NO_DB_ALIAS:
        return
    from django.conf import settings

    with connection.cursor() as cursor:
        # DB_SCHEMA is validated as a plain identifier in settings, so quoting is safe.
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"')


class TenantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant'
    label = 'tenant'

    def ready(self):
        connection_created.connect(ensure_schema, dispatch_uid='ensure_db_schema')
