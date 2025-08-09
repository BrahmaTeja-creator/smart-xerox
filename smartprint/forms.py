# smartprint/forms.py
from django import forms
from django.forms import formset_factory # Import formset_factory
from .models import PrintJob, PredefinedDocument

class PrintJobItemForm(forms.ModelForm): # Renamed to PrintJobItemForm for clarity
    # Add a field for predefined documents, not directly part of PrintJob model
    predefined_document = forms.ModelChoiceField(
        queryset=PredefinedDocument.objects.all(),
        required=False,
        empty_label="-- Select a predefined document --",
        label="Select a common document"
    )

    class Meta:
        model = PrintJob # Still refers to the PrintJob model
        # Added 'total_pages' to the fields
        fields = ['document', 'total_pages', 'num_copies', 'is_color', 'color_pages_info', 'needs_binding']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'total_pages': forms.NumberInput(attrs={'min': 1, 'class': 'form-control', 'placeholder': 'Enter total pages'}),
            'num_copies': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
            'is_color': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'color_pages_info': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional: e.g., Pages 1-5 color, rest B&W', 'class': 'form-control'}),
            'needs_binding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'document': 'Upload Your Document (PDF/Image)',
            'total_pages': 'Total Pages in Document',
            'num_copies': 'Number of Copies',
            'is_color': 'Print in Color (Check for Color, Uncheck for B&W)',
            'color_pages_info': 'Specific Color Pages (Optional)',
            'needs_binding': 'Add Binding',
        }

    # Custom validation for either document upload or predefined document selection
    def clean(self):
        cleaned_data = super().clean()
        document = cleaned_data.get('document')
        predefined_document = cleaned_data.get('predefined_document')
        total_pages = cleaned_data.get('total_pages')

        # Only apply validation if the form is not marked for deletion (for formsets)
        # This is important for when you add "delete" functionality to formset items
        if self.prefix and self.data.get(f'{self.prefix}-DELETE'):
            return cleaned_data

        if not document and not predefined_document:
            raise forms.ValidationError(
                "You must either upload a document or select a predefined document for this item."
            )
        if document and predefined_document:
            raise forms.ValidationError(
                "Please choose only one: upload a document OR select a predefined document for this item."
            )

        # Ensure total_pages is provided if a document is selected/uploaded
        if (document or predefined_document) and (total_pages is None or total_pages <= 0):
            self.add_error('total_pages', "Total pages must be a positive number for printing this item.")

        return cleaned_data

# Create a formset for PrintJobItemForm
# extra=1: Start with 1 empty form
# can_delete=True: Allows deleting forms in the formset (useful for frontend)
PrintJobItemFormset = formset_factory(PrintJobItemForm, extra=1, can_delete=True)