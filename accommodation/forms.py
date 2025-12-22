from django import forms
from django.forms.widgets import FileInput
from accommodation.models import Accommodation, AccommodationImage


class MultipleFileInput(FileInput):
    """Custom widget to handle multiple file uploads"""

    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True})
        self.attrs = attrs


class MultipleFileField(forms.FileField):
    """Custom field to handle multiple file uploads"""
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if isinstance(data, list):
            return [super(MultipleFileField, self).clean(d, initial) for d in data]
        else:
            return super(MultipleFileField, self).clean(data, initial)


class AccommodationForm(forms.ModelForm):
    # Add field for multiple images
    additional_images = MultipleFileField(
        required=False,
        label='Additional Images'
    )

    class Meta:
        model = Accommodation
        fields = '__all__'
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'})
        }
        exclude = ('created_by', 'is_active')
        labels = {
            'image': 'Primary Image'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'additional_images':
                field.widget.attrs.update({
                    'class': 'form-control',
                    'accept': 'image/*'
                })
            else:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'autocomplete': 'on'
                })

            if isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-check-input'})

        if 'description' in self.fields:
            self.fields['description'].widget.attrs['style'] = 'height: 150px;'