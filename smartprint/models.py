# smartprint/models.py

from django.db import models
from django.contrib.auth.models import User

# This model stores the global pricing information, editable by the admin.
class PriceSetting(models.Model):
    price_per_bw_page = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    price_per_color_page = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    binding_cost = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    payment_policy = models.CharField(max_length=20, choices=[('FULL_ONLY', 'Full Payment Only'), ('ADVANCE_ALLOWED', 'Advance Payment Allowed')], default='FULL_ONLY')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Current Price Settings"


# This model represents a complete order submitted by a student.
class PrintOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('ADVANCE_PAID', 'Advance Paid'),
        ('FULL_PAID', 'Full Paid'),
        ('REFUNDED', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_estimated_cost = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    amount_paid = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    priority = models.IntegerField(default=0)
    is_emergency = models.BooleanField(default=False) # For faculty/emergency requests

    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"


# This model represents a single document (item) within a PrintOrder.
# The previous PrintJob will now conceptually be a PrintJobItem.
class PrintJob(models.Model): # Keeping class name as PrintJob for simpler migration path, but it's an "item"
    order = models.ForeignKey(PrintOrder, on_delete=models.CASCADE, related_name='items') # Link to the parent order
    document = models.FileField(upload_to='print_documents/')
    total_pages = models.IntegerField(default=0) # Number of pages/images in this specific document
    num_copies = models.IntegerField(default=1) # Copies of THIS specific document
    
    # Customization for THIS document
    is_color = models.BooleanField(default=False) # True if color, False if B&W
    # Keeping color_pages_info for more granular control if needed, but is_color is simpler for now
    color_pages_info = models.TextField(blank=True, null=True) 
    needs_binding = models.BooleanField(default=False)

    # Cost of this specific item (document)
    item_estimated_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0.00) 
    
    is_printed_by_admin = models.BooleanField(default=False) # Tracks if this specific document has been printed

    def __str__(self):
        return f"Item {self.id} for Order {self.order.id}: {self.document.name.split('/')[-1]}"


# This model stores common documents that the admin can upload.
class PredefinedDocument(models.Model):
    title = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='predefined_documents/')
    total_pages = models.IntegerField(default=0) # Store page count for predefined docs
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title