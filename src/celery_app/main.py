from celery import Celery

from app.core.config import settings

celery_app = Celery(broker=settings.rabbit_url, backend='rpc://')

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    enable_utc=True,
    include=['celery_app.tasks'],
    task_routes={
        'celery_app.tasks.*': 'default',
    },
)
