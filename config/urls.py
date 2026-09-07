"""URL configuration for the To-Do app."""
from django.contrib import admin
from django.urls import path

from todos import views

urlpatterns = [
    path("", views.task_list, name="task-list"),
    path("create/", views.create_task, name="task-create"),
    path("tasks/<int:pk>/edit/", views.edit_task, name="task-edit"),
    path("tasks/<int:pk>/toggle/", views.toggle_task, name="task-toggle"),
    path("tasks/<int:pk>/delete/", views.delete_task, name="task-delete"),
    path("health/", views.health_check, name="health-check"),
    path("admin/", admin.site.urls),
]
