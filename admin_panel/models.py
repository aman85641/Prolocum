from django.db import models

# Create your models here.
# admin/models.py mein add karo (existing code ke neeche)

class City(models.Model):
    name  = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['state', 'name']

    def __str__(self):
        return f"{self.name}, {self.state}"