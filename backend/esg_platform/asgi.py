"""
ASGI config for esg_platform.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esg_platform.settings')

application = get_asgi_application()
