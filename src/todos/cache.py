from django.core.cache import cache

from .models import Task

LIST_CACHE_KEY = "todos:list"
LIST_CACHE_TTL_SECONDS = 60


def get_cached_task_list():
    # Returns (tasks, from_cache).
    tasks = cache.get(LIST_CACHE_KEY)
    if tasks is not None:
        return tasks, True

    tasks = list(Task.objects.all())
    cache.set(LIST_CACHE_KEY, tasks, LIST_CACHE_TTL_SECONDS)
    return tasks, False


def invalidate_task_list_cache():
    cache.delete(LIST_CACHE_KEY)
