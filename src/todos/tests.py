import pytest
from django.core.cache import cache
from django.urls import reverse

from .models import Task


@pytest.mark.django_db
def test_health_check(client):
    response = client.get(reverse("health-check"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_empty_list(client):
    response = client.get(reverse("task-list"))
    assert response.status_code == 200
    assert b"No tasks yet" in response.content


@pytest.mark.django_db
def test_create_list_toggle_delete_round_trip(client):
    cache.clear()

    response = client.post(reverse("task-create"), {"title": "Buy milk", "description": "2%"})
    assert response.status_code == 302
    assert Task.objects.filter(title="Buy milk").exists()

    response = client.get(reverse("task-list"))
    assert b"Buy milk" in response.content

    task = Task.objects.get(title="Buy milk")
    assert task.is_done is False

    response = client.post(reverse("task-toggle", args=[task.pk]))
    assert response.status_code == 302
    task.refresh_from_db()
    assert task.is_done is True

    response = client.post(reverse("task-delete", args=[task.pk]))
    assert response.status_code == 302
    assert not Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
def test_edit_task(client):
    task = Task.objects.create(title="Old title")
    response = client.post(
        reverse("task-edit", args=[task.pk]), {"title": "New title", "description": ""}
    )
    assert response.status_code == 302
    task.refresh_from_db()
    assert task.title == "New title"


@pytest.mark.django_db
def test_list_is_cached_after_first_read(client):
    cache.clear()
    Task.objects.create(title="Cache me")

    first = client.get(reverse("task-list"))
    assert b"database" in first.content

    second = client.get(reverse("task-list"))
    assert b"Redis cache" in second.content or b"cache" in second.content.lower()


@pytest.mark.django_db
def test_write_invalidates_cache(client):
    cache.clear()
    client.get(reverse("task-list"))  # warms the cache (empty list)

    client.post(reverse("task-create"), {"title": "Fresh task", "description": ""})

    response = client.get(reverse("task-list"))
    assert b"Fresh task" in response.content
