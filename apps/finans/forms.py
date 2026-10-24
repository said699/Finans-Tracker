from django import forms
from apps.finans.models import Payment, PayCategory


class AddPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ('user', 'amount', 'currency', 'category')

class AddCategoryForm(forms.ModelForm):
    class Meta:
        model = PayCategory
        fields = ('name', 'color')