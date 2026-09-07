from django.db import models


class Task(models.Model):
    # Explicit manager so Pylance/pyright can resolve Task.objects.
    objects = models.Manager()

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_done = models.BooleanField(default=False)  # type: ignore[reportArgumentType]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.title)

    def toggle_done(self) -> None:
        self.is_done = not self.is_done
        self.save(update_fields=["is_done", "updated_at"])
