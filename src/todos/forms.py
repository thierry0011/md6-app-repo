from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What needs doing?", "maxlength": 200}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Details (optional)"}),
        }
