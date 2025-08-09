from django.contrib import admin

# Register your models here.
# smartprint/admin.py

from django.contrib import admin
from .models import PriceSetting, PrintOrder, PrintJob, PredefinedDocument

# Register your models here.
admin.site.register(PriceSetting)
admin.site.register(PrintOrder)
admin.site.register(PrintJob)
admin.site.register(PredefinedDocument)