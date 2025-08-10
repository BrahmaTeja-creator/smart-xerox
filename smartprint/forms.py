# smartprint/forms.py
from django import forms
from django.forms import formset_factory
from .models import PrintJob, PredefinedDocument

class PrintJobItemForm(forms.ModelForm):
    predefined_document = forms.ModelChoiceField(
        queryset=PredefinedDocument.objects.all(),
        required=False,
        empty_label="-- Select a predefined document --",
        label="Select a common document"
    )

    # Override the 'document' field to make it optional at the form level
    document = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='Upload Your Document (PDF/Image)'
    )

    class Meta:
        model = PrintJob
        fields = [
            'predefined_document',
            'document',
            'total_pages',
            'num_copies',
            'is_color',
            'color_pages_info',
            'needs_binding'
        ]
        widgets = {
            'total_pages': forms.NumberInput(attrs={'min': 1, 'class': 'form-control', 'placeholder': 'Enter total pages'}),
            'num_copies': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
            'is_color': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'color_pages_info': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional: e.g., Pages 1-5 color, rest B&W',
                'class': 'form-control'
            }),
            'needs_binding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'total_pages': 'Total Pages in Document',
            'num_copies': 'Number of Copies',
            'is_color': 'Print in Color (Check for Color, Uncheck for B&W)',
            'color_pages_info': 'Specific Color Pages (Optional)',
            'needs_binding': 'Add Binding',
        }

    def clean(self):
        cleaned_data = super().clean()
        document = cleaned_data.get('document')
        predefined_document = cleaned_data.get('predefined_document')
        total_pages = cleaned_data.get('total_pages')

        # Skip validation if marked for deletion in formset
        if self.prefix and self.data.get(f'{self.prefix}-DELETE'):
            return cleaned_data

        # Either-or validation
        if not document and not predefined_document:
            raise forms.ValidationError(
                "You must either upload a document or select a predefined document for this item."
            )
        if document and predefined_document:
            raise forms.ValidationError(
                "Please choose only one: upload a document OR select a predefined document for this item."
            )

        # Page count validation
        if (document or predefined_document) and (total_pages is None or total_pages <= 0):
            self.add_error('total_pages', "Total pages must be a positive number for printing this item.")

        return cleaned_data


PrintJobItemFormset = formset_factory(PrintJobItemForm, extra=1, can_delete=True)
