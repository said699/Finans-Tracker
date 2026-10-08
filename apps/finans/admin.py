from django.contrib import admin
from .models import PayCategory, Payment

admin.site.register(Payment)
admin.site.register(PayCategory)