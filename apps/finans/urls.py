from django.urls import path
from .views import HomeHistoryView, AddPaymentView, AddCategoryView, PaymentDetView, payment_delete, ListCategory, category_delete

app_name = 'finans'

urlpatterns = [
    path('home/', HomeHistoryView.as_view(), name='home'),
    path('history/<int:pk>/', PaymentDetView.as_view(), name='payment_details'),
    path('category/add/', AddCategoryView.as_view(), name='add_category'),
    path('payment/add/', AddPaymentView.as_view(), name='add_payment'),
    path('payment/delete/<int:pk>/', payment_delete, name='payment_delete'),
    path('categories/', ListCategory.as_view(), name='category_list'),
    path('category/delete/<int:pk>/', category_delete, name='category_delete')
]