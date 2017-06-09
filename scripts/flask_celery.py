from celery import Celery
from cyc_config import cyc_config as cfg


def make_celery(app):
    celery = Celery(app.import_name, broker=cfg.RABBITMQ_URI)
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
