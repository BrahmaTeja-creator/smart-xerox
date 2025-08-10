# smartprint/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404, JsonResponse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_POST
from .models import PrintJob, PriceSetting, PredefinedDocument, PrintOrder, User
from .forms import PrintJobItemForm, PrintJobItemFormset
import json # Import json for JSON serialization

# Import PyMuPDF for PDF page counting
try:
    import fitz # PyMuPDF
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
except ImportError:
    fitz = None
    print("Warning: PyMuPDF (fitz) not installed. PDF page counting will not work.")


# Helper function to check if a user is an admin (superuser)
def is_admin(user):
    """Checks if the user is authenticated and is a superuser."""
    return user.is_authenticated and user.is_superuser


# Helper function to calculate the cost of a print job item
def calculate_item_cost(item_data, price_settings):
    """
    Calculates the estimated cost of a single PrintJob item.
    item_data is a dictionary (from AJAX) or a PrintJob instance (from form submission).
    """
    # Safely get values, converting to int/bool. Use .get() with defaults for dicts.
    # For PrintJob instances, access attributes directly.
    num_copies = int(item_data.get('num_copies', 1)) if isinstance(item_data, dict) else int(item_data.num_copies)
    total_pages = int(item_data.get('total_pages', 0)) if isinstance(item_data, dict) else int(item_data.total_pages)
    
    # Checkbox values from JS FormData are 'true' or 'false' strings, convert to Python bool
    is_color_str = item_data.get('is_color', 'false') if isinstance(item_data, dict) else str(item_data.is_color).lower()
    is_color = is_color_str == 'true'

    needs_binding_str = item_data.get('needs_binding', 'false') if isinstance(item_data, dict) else str(item_data.needs_binding).lower()
    needs_binding = needs_binding_str == 'true'

    # Ensure numeric types are valid
    if num_copies < 1: num_copies = 1
    if total_pages < 0: total_pages = 0

    cost = 0

    if is_color:
        cost += (total_pages * price_settings.price_per_color_page)
    else:
        cost += (total_pages * price_settings.price_per_bw_page)

    if needs_binding:
        cost += price_settings.binding_cost

    return cost * num_copies


# ----------------------------------------------------
#               User-Facing Views
# ----------------------------------------------------

def home(request):
    """Renders the homepage template."""
    return render(request, 'smartprint/home.html')

@login_required
def user_panel(request):
    """
    Renders the student's user panel and handles print order submission with multiple items.
    Displays user's submitted orders.
    """
    # Fetch current price settings (or use defaults if none exist)
    price_settings, created = PriceSetting.objects.get_or_create(pk=1) # Assuming a single price setting entry

    if request.method == 'POST':
        formset = PrintJobItemFormset(request.POST, request.FILES, prefix='items') # Use prefix for formset
        
        if formset.is_valid():
            # Create a new PrintOrder for this submission
            print_order = PrintOrder.objects.create(user=request.user)
            total_order_cost = 0

            for form in formset:
                # Check if the form is marked for deletion (if can_delete=True in formset_factory)
                if form.cleaned_data.get('DELETE'):
                    continue # Skip deleted forms

                # Ensure a document or predefined document is selected for non-deleted forms
                if not form.cleaned_data.get('document') and not form.cleaned_data.get('predefined_document'):
                    # This case should ideally be caught by form validation
                    continue # Skip if no document is associated with this form item

                print_job_item = form.save(commit=False)
                print_job_item.order = print_order # Link item to the new order

                # Handle predefined document vs. uploaded document
                predefined_doc_obj = form.cleaned_data.get('predefined_document')
                if predefined_doc_obj:
                    print_job_item.document = predefined_doc_obj.document_file
                    print_job_item.total_pages = predefined_doc_obj.total_pages # Get pages from predefined
                else:
                    # If a document was uploaded, try to get page count using PyMuPDF
                    uploaded_file = form.cleaned_data.get('document') # Get uploaded file from cleaned_data
                    if uploaded_file and fitz:
                        try:
                            # Save the uploaded file temporarily to count pages
                            # This is a more robust way to handle in-memory uploaded files
                            file_name = default_storage.save(uploaded_file.name, ContentFile(uploaded_file.read()))
                            temp_path = default_storage.path(file_name)

                            doc = fitz.open(temp_path)
                            print_job_item.total_pages = doc.page_count
                            doc.close()
                            default_storage.delete(file_name) # Clean up temp file
                        except Exception as e:
                            print(f"Error counting PDF pages for uploaded file: {e}")
                            print_job_item.total_pages = 0 # Default to 0 if error
                    else:
                        # If no file or fitz not available, use total_pages from form input
                        print_job_item.total_pages = form.cleaned_data.get('total_pages', 0)


                # Calculate estimated cost for this item
                # Pass cleaned_data dict to calculate_item_cost for consistency
                print_job_item.item_estimated_cost = calculate_item_cost(form.cleaned_data, price_settings)
                print_job_item.save() # Save the PrintJob instance
                total_order_cost += print_job_item.item_estimated_cost

            # Update total cost of the PrintOrder
            print_order.total_estimated_cost = total_order_cost
            print_order.save()

            # Redirect to the success page after submission
            return redirect('order_success') 
        else:
            pass # Form will be re-rendered with errors
    else:
        formset = PrintJobItemFormset(prefix='items') # Create an empty formset for GET requests

    predefined_docs = PredefinedDocument.objects.all()
    # Ensure predefined_doc_pages is always a dictionary, even if no predefined docs exist
    # Convert QuerySet to a dict and then to JSON string
    predefined_doc_pages_map = {str(doc.id): doc.total_pages for doc in predefined_docs} # Convert ID to string key
    predefined_doc_pages_json = json.dumps(predefined_doc_pages_map)
    
    # Fetch current user's print orders for display
    user_print_orders = PrintOrder.objects.filter(user=request.user).order_by('-requested_at')

    context = {
        'formset': formset, # Pass the formset to the template
        'predefined_docs': predefined_docs,
        'predefined_doc_pages': predefined_doc_pages_json, # Pass the JSON string here
        'user': request.user,
        'user_print_orders': user_print_orders,
        'price_settings': price_settings,
    }
    return render(request, 'smartprint/user_panel.html', context)

def order_success(request): # This is the order_success view
    """Renders a success page after an order is placed."""
    return render(request, 'smartprint/order_success.html')

@require_POST # Ensures this view only accepts POST requests
def calculate_cost_ajax(request):
    """
    Calculates the estimated cost of a print order (sum of items) via AJAX.
    Expects POST data for multiple formset items.
    """
    try:
        # Get price settings
        price_settings = PriceSetting.objects.first()
        if not price_settings:
            return JsonResponse({'error': 'Price settings not found. Please configure in admin.'}, status=500)

        total_order_cost = 0
        
        # Determine the number of forms submitted via AJAX
        # Use TOTAL_FORMS from the formset management data
        total_forms = int(request.POST.get('items-TOTAL_FORMS', 0))

        for i in range(total_forms):
            # Check if this specific form is marked for deletion in AJAX (if frontend sends it)
            if request.POST.get(f'items-{i}-DELETE') == 'true':
                continue # Skip deleted forms

            # Extract data for each item, providing default values for numbers
            item_data_for_calc = {
                'num_copies': request.POST.get(f'items-{i}-num_copies') or '1', # Default to '1' string
                'total_pages': request.POST.get(f'items-{i}-total_pages') or '0', # Default to '0' string
                'is_color': request.POST.get(f'items-{i}-is_color') or 'false', # Default to 'false' string
                'needs_binding': request.POST.get(f'items-{i}-needs_binding') or 'false', # Default to 'false' string
            }
            
            # Calculate cost for this item and add to total order cost
            total_order_cost += calculate_item_cost(item_data_for_calc, price_settings)

        return JsonResponse({'estimated_cost': f'₹ {total_order_cost:.2f}'})

    except Exception as e:
        # Catch any unexpected errors and return a JSON error response
        print(f"Error in calculate_cost_ajax: {e}") # Log the error for debugging
        return JsonResponse({'error': f'An unexpected error occurred during cost calculation: {e}'}, status=500)

@require_POST
def get_page_count_ajax(request):
    """
    Receives an uploaded file via AJAX, counts its pages using PyMuPDF,
    and returns the page count as JSON.
    """
    if 'document' not in request.FILES:
        return JsonResponse({'error': 'No document file provided.'}, status=400)

    uploaded_file = request.FILES['document']

    if not fitz:
        return JsonResponse({'error': 'PyMuPDF not installed on server.'}, status=500)

    try:
        # Save the uploaded file temporarily to count pages
        file_name = default_storage.save(uploaded_file.name, ContentFile(uploaded_file.read()))
        temp_path = default_storage.path(file_name)

        doc = fitz.open(temp_path)
        page_count = doc.page_count
        doc.close()
        default_storage.delete(file_name) # Clean up temp file

        return JsonResponse({'total_pages': page_count})

    except Exception as e:
        print(f"Error processing PDF for page count: {e}")
        return JsonResponse({'error': f'Could not process document for page count: {e}'}, status=500)


# ----------------------------------------------------
#               Admin-Facing Views
# ----------------------------------------------------

@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Renders the admin dashboard.
    Displays pending orders and basic analytics.
    """
    # Fetch all pending orders, ordered from oldest to newest
    # Use select_related to fetch user to avoid N+1 queries
    pending_orders = PrintOrder.objects.filter(status='PENDING').order_by('requested_at').select_related('user')

    # Basic Data Analysis for the dashboard (based on PrintOrder)
    # Filter by requested_at for PrintOrder
    total_jobs_today = PrintOrder.objects.filter(requested_at__date=timezone.now().date()).count()

    total_earnings_today = PrintOrder.objects.filter(
        requested_at__date=timezone.now().date(),
        payment_status__in=['FULL_PAID', 'ADVANCE_PAID']
    ).aggregate(total=Sum('total_estimated_cost'))['total'] or 0

    # Calculate total pages printed today for COMPLETED items within COMPLETED orders
    # This requires summing across related PrintJob items
    total_pages_printed_today = PrintOrder.objects.filter(
        completed_at__date=timezone.now().date(),
        status='COMPLETED'
    ).aggregate(total=Sum('items__total_pages'))['total'] or 0 # Sum total_pages from related PrintJob items
    
    context = {
        'pending_orders': pending_orders, # Pass orders instead of jobs
        'total_jobs_today': total_jobs_today,
        'total_earnings_today': total_earnings_today,
        'total_pages_printed_today': total_pages_printed_today,
    }
    return render(request, 'smartprint/admin_dashboard.html', context)

@user_passes_test(is_admin)
def admin_profile(request):
    """
    Renders the admin profile and analytics page.
    Displays earnings and other detailed statistics.
    """
    # Fetch data for analytics here
    total_earnings_all_time = PrintOrder.objects.filter(
        payment_status__in=['FULL_PAID', 'ADVANCE_PAID']
    ).aggregate(total=Sum('total_estimated_cost'))['total'] or 0

    total_pages_all_time = PrintOrder.objects.filter(
        status='COMPLETED'
    ).aggregate(total=Sum('items__total_pages'))['total'] or 0
    
    # You can add more detailed analytics here, e.g.,
    # orders_by_status = PrintOrder.objects.values('status').annotate(count=Count('id'))
    # popular_predefined_docs = PredefinedDocument.objects.annotate(num_uses=Count('printjob__id')).order_by('-num_uses')[:5]

    context = {
        'total_earnings_all_time': total_earnings_all_time,
        'total_pages_all_time': total_pages_all_time,
        'user': request.user, # Pass current user info
        # 'orders_by_status': orders_by_status,
    }
    return render(request, 'smartprint/admin_profile.html', context)


@user_passes_test(is_admin)
def approve_order(request, order_id): # Changed to approve_order
    """Updates an order's status to 'APPROVED'."""
    order = get_object_or_404(PrintOrder, pk=order_id)
    order.status = 'APPROVED'
    order.approved_at = timezone.now()
    order.save()
    return redirect('admin_dashboard')

@user_passes_test(is_admin)
def reject_order(request, order_id): # Changed to reject_order
    """Updates an order's status to 'REJECTED'."""
    order = get_object_or_404(PrintOrder, pk=order_id)
    order.status = 'REJECTED'
    order.save()
    return redirect('admin_dashboard')

@user_passes_test(is_admin)
def complete_order(request, order_id):
    """Updates an order's status to 'COMPLETED'."""
    order = get_object_or_404(PrintOrder, pk=order_id)
    order.status = 'COMPLETED'
    order.completed_at = timezone.now() # Set completion timestamp
    order.save()
    return redirect('admin_dashboard')

@user_passes_test(is_admin)
def mark_as_paid_order(request, order_id):
    """Updates an order's payment_status to 'FULL_PAID'."""
    order = get_object_or_404(PrintOrder, pk=order_id)
    order.payment_status = 'FULL_PAID' # Or 'ADVANCE_PAID' if you want to differentiate
    order.save()
    return redirect('admin_dashboard')

@user_passes_test(is_admin)
def print_job_document(request, order_id, item_id): # Now takes order_id and item_id
    """
    Marks a specific print job document as 'printed' and then serves an HTML page
    that embeds the PDF and triggers the browser's print dialog.
    """
    order = get_object_or_404(PrintOrder, pk=order_id)
    job_item = get_object_or_404(PrintJob, pk=item_id, order=order) # Get specific item within order

    # Check if the document file exists
    if not job_item.document:
        raise Http404("Document not found for this job item.")

    # Mark as printed if it hasn't been already
    if not job_item.is_printed_by_admin:
        job_item.is_printed_by_admin = True
        job_item.save()

    # Pass the document URL to a new template that will embed and print it
    context = {
        'document_url': job_item.document.url,
        'order_id': order.id,
        'item_id': job_item.id,
    }
    return render(request, 'smartprint/print_viewer.html', context)