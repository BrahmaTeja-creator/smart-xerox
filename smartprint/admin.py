# smartprint/admin.py
from django.contrib import admin
from django.db.models import Sum, F
from django.utils import timezone
from .models import PriceSetting, PrintOrder, PrintJob, PredefinedDocument

@admin.action(description="Approve selected orders and update totals")
def approve_orders(modeladmin, request, queryset):
    price_settings = PriceSetting.objects.first()

    for order in queryset:
        if order.status != "APPROVED":  # avoid double-counting
            order.status = "APPROVED"
            order.approved_at = timezone.now()
            order.save()

            total_pages = 0
            total_cost = 0

            for job in order.items.all():
                pages_for_job = job.total_pages * job.num_copies
                total_pages += pages_for_job
                total_cost += job.item_estimated_cost
                job.is_printed_by_admin = True
                job.save()

            # Here, instead of Shop, we update global stats.
            # You could store in PriceSetting or a separate Stats model.
            if price_settings:
                # Example: If you had these fields in PriceSetting
                if hasattr(price_settings, 'total_earnings'):
                    price_settings.total_earnings = F('total_earnings') + total_cost
                if hasattr(price_settings, 'total_pages_printed'):
                    price_settings.total_pages_printed = F('total_pages_printed') + total_pages
                price_settings.save()

@admin.register(PrintOrder)
class PrintOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_estimated_cost", "payment_status", "requested_at")
    actions = [approve_orders]

@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "total_pages", "num_copies", "is_color", "needs_binding", "item_estimated_cost", "is_printed_by_admin")
    list_filter = ("is_color", "needs_binding", "is_printed_by_admin")

admin.site.register(PriceSetting)
admin.site.register(PredefinedDocument)
