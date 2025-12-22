from django import forms
from django.forms import DateTimeInput

from .models import Announcement

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = '__all__'
        widgets = {
            'publish_date': DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'autocomplete': 'on'
            }, format='%Y-%m-%dT%H:%M'),

            'expiry_date': DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'autocomplete': 'on'
            }, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control',
                                       'autocomplete': 'on'
                                       })

            if isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-check-input'})

        if 'content' in self.fields:
            self.fields['content'].widget.attrs['style'] = 'height: 150px;'
        for name in ['publish_date', 'expiry_date']:
            if self.instance.pk and name in self.fields:
                value = getattr(self.instance, name)
                if value:
                    self.fields[name].initial = value.strftime('%Y-%m-%dT%H:%M')