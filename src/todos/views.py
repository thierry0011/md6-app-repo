from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task

CACHE_KEY = "todos:list"
CACHE_TTL_SECONDS = 60


def _invalidate_list_cache():
    cache.delete(CACHE_KEY)


def task_list(request):
    """Reads go through Redis first (write-through invalidated on every
    create/edit/toggle/delete below, plus a short TTL as a safety net) so
    the list page is demonstrably cache-accelerated, not just DB-backed."""
    tasks = cache.get(CACHE_KEY)
    from_cache = tasks is not None
    if tasks is None:
        tasks = list(Task.objects.all())
        cache.set(CACHE_KEY, tasks, CACHE_TTL_SECONDS)
    return render(
        request,
        "todos/index.html",
        {"tasks": tasks, "form": TaskForm(), "from_cache": from_cache},
    )


def create_task(request):
    if request.method != "POST":
        return redirect("task-list")

    form = TaskForm(request.POST)
    if form.is_valid():
        form.save()
        _invalidate_list_cache()
        messages.success(request, "Task created.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect("task-list")


def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            _invalidate_list_cache()
            messages.success(request, "Task updated.")
            return redirect("task-list")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm(instance=task)

    return render(request, "todos/task_form.html", {"form": form, "task": task})


@require_POST
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.is_done = not task.is_done
    task.save(update_fields=["is_done", "updated_at"])
    _invalidate_list_cache()
    return redirect("task-list")


@require_POST
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    _invalidate_list_cache()
    messages.success(request, "Task deleted.")
    return redirect("task-list")


def health_check(request):
    """Liveness check for the ALB target groups. Deliberately does not touch
    the database or cache so a slow/unavailable dependency never flaps ECS
    task health."""
    return JsonResponse({"status": "ok"})
