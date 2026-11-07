from django import forms
from apps.finans.models import Payment, PayCategory, Earnings, EarningCategory


class AddPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'currency', 'category', 'note']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields['category'].queryset = PayCategory.objects.filter(user=user)    

class AddCategoryForm(forms.ModelForm):
    class Meta:
        model = PayCategory
        fields = ['name', 'color']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
            self.user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        if self.user and PayCategory.objects.filter(user=self.user, name=name).exists():
            raise forms.ValidationError('У вас уже есть категория с таким названием.')
            
        return name



class AddEarningCategoryForm(forms.ModelForm):
    class Meta:
        model = EarningCategory
        fields = ['name', 'color']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        }
       
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
       
    def clean_name(self):
        name = self.cleaned_data.get('name')
               
        if self.user and EarningCategory.objects.filter(user=self.user, name=name).exists():
            raise forms.ValidationError('У вас уже есть категория с таким названием.')
                   
        return name

class AddEarningForm(forms.ModelForm):
    class Meta:
        model = Earnings
        fields = ['amount', 'currency', 'category', 'note']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
        if self.user:
            self.fields['category'].queryset = EarningCategory.objects.filter(user=self.user)    