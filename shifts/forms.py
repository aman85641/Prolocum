# shifts/forms.py

from django import forms
from .models import Shift, ShiftReview
from django.utils import timezone

DOCTOR_QUALIFICATIONS = ['mbbs', 'bams', 'bhms', 'bams_bhms']
NURSE_QUALIFICATIONS  = ['gnm', 'bsc_nursing', 'anm', 'msc_nursing']

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = [
            'hospital_name', 'ward_type', 'bed_count',
            'address', 'landmark', 'area', 'city',
            'location_link',  # ← ADD KARO
            'target_role', 'qualification_required', 'shift_type',
            'start_date', 'end_date', 'start_time', 'end_time',
            'pay', 'requirements', 'is_urgent',
        ]
        widgets = {
            'start_date':   forms.DateInput(attrs={'type': 'date'}),
            'end_date':     forms.DateInput(attrs={'type': 'date'}),
            'start_time':   forms.TimeInput(attrs={'type': 'time'}),
            'end_time':     forms.TimeInput(attrs={'type': 'time'}),
            'requirements': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Write one requirement per line\nCarry ID Card\nArrive 15 minutes early'
            }),
        }
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now().date():
            raise forms.ValidationError('Shift date cannot be in the past.')
        return start_date
    
    def clean(self):
        cleaned_data = super().clean()
        shift_type = cleaned_data.get('shift_type')
        end_date   = cleaned_data.get('end_date')
        start_date = cleaned_data.get('start_date')
        role       = cleaned_data.get('target_role')
        qual       = cleaned_data.get('qualification_required')

        if shift_type == 'multiple' and not end_date:
            self.add_error('end_date', 'End date is required for multiple-day shifts.')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date.')

        # Qualification vs role validation
        if role == 'doctor' and qual in NURSE_QUALIFICATIONS:
            self.add_error('qualification_required', 'Please select a doctor qualification for the doctor role.')
        elif role == 'nurse' and qual in DOCTOR_QUALIFICATIONS:
            self.add_error('qualification_required', 'Please select a nurse qualification for the nurse role.')

        return cleaned_data


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, '⭐' * i) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-radio'}),
        label='Rating'
    )

    class Meta:
        model = ShiftReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience (optional)...',
                'class': 'form-control',
            }),
        }