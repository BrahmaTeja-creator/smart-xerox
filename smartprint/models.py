# smartprint/models.py

from django.db import models
from django.contrib.auth.models import User

# Import PyMuPDF for PDF page counting in models
try:
    import fitz # PyMuPDF
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
except ImportError:
    fitz = None
    print("Warning: PyMuPDF (fitz) not installed. PDF page counting in models will not work.")


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
class PrintJob(models.Model):
    order = models.ForeignKey(PrintOrder, on_delete=models.CASCADE, related_name='items')
    document = models.FileField(upload_to='print_documents/')
    total_pages = models.IntegerField(default=0)
    num_copies = models.IntegerField(default=1)
    
    is_color = models.BooleanField(default=False)
    color_pages_info = models.TextField(blank=True, null=True) 
    needs_binding = models.BooleanField(default=False)

    item_estimated_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0.00) 
    
    is_printed_by_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"Item {self.id} for Order {self.order.id}: {self.document.name.split('/')[-1]}"


# This model stores common documents that the admin can upload.
class PredefinedDocument(models.Model):
    title = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='predefined_documents/')
    total_pages = models.IntegerField(default=0) # Field to store page count
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    # Override save method to automatically count pages
    def save(self, *args, **kwargs):
        if self.document_file and fitz: # Ensure a file is uploaded and PyMuPDF is available
            # If the file has changed or pages are not set, try to count
            if not self.pk or self.document_file != PredefinedDocument.objects.get(pk=self.pk).document_file:
                try:
                    # Open the file directly from Django's FileField
                    doc = fitz.open(stream=self.document_file.read(), filetype="pdf") # Use stream for in-memory file
                    self.total_pages = doc.page_count
                    doc.close()
                    # Reset file pointer after reading for Django to save it correctly
                    self.document_file.seek(0) 
                except Exception as e:
                    print(f"Error counting pages for predefined document {self.title}: {e}")
                    self.total_pages = 0 # Default to 0 if error
        super().save(*args, **kwargs) # Call the original save method

