from django import forms
from .models import Vacancy


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = [
            'hospital_name', 'location', 'city', 'state',
            'staff_type', 'designation', 'ward_type', 'bed_capacity',
            'doctor_qualification', 'nurse_qualification', 'experience_required',
            'shift_type', 'start_date', 'end_date', 'start_time', 'end_time',
            'shift_label', 
            'salary', 'job_description', 'contact_email', 'contact_phone', 'is_urgent',
        ]
        widgets = {
            'start_date':       forms.DateInput(attrs={'type': 'date'}),
            'end_date':         forms.DateInput(attrs={'type': 'date'}),
            'start_time':       forms.TimeInput(attrs={'type': 'time'}),
            'end_time':         forms.TimeInput(attrs={'type': 'time'}),
            'job_description':  forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write job description...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False

    def clean(self):
        cleaned_data = super().clean()
        end_date   = cleaned_data.get('end_date')
        start_date = cleaned_data.get('start_date')

        if start_date and end_date and end_date > start_date:
            self.add_error('end_date', 'Last date of application must be before the joining date.')

        return cleaned_data