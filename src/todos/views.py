from django.contrib import messages
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cache import get_cached_task_list, invalidate_task_list_cache
from .forms import TaskForm
from .models import Task


def _flash_form_errors(request: HttpRequest, form: TaskForm) -> None:
    # Flattens form validation errors into the messages framework.
    for field, errors in (form.errors or {}).items():
        for error in errors:
            messages.error(request, f"{field}: {error}")


def task_list(request):
    tasks, from_cache = get_cached_task_list()
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
        invalidate_task_list_cache()
        messages.success(request, "Task created.")
    else:
        _flash_form_errors(request, form)

    return redirect("task-list")


def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            invalidate_task_list_cache()
            messages.success(request, "Task updated.")
            return redirect("task-list")
        _flash_form_errors(request, form)
    else:
        form = TaskForm(instance=task)

    return render(request, "todos/task_form.html", {"form": form, "task": task})


@require_POST
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.toggle_done()
    invalidate_task_list_cache()
    return redirect("task-list")


@require_POST
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    invalidate_task_list_cache()
    messages.success(request, "Task deleted.")
    return redirect("task-list")


def health_check(request):
    # ALB health check: no DB/cache dependency.
    return JsonResponse({"status": "ok"})
