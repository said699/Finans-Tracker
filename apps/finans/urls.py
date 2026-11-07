from django.urls import path
from .views_pay import Payments, AddPaymentView, AddCategoryView, PaymentDetView, payment_delete, ListCategory, category_delete
from .views_earn import EarningDetView, earning_delete, ListEarnCategory, EarningsView, AddEarningCategoryView, AddEarningView, earn_category_delete

app_name = 'finans'

urlpatterns = [
    path('payments/', Payments.as_view(), name='payments'),
    path('history/pay/<int:pk>/', PaymentDetView.as_view(), name='payment_details'),
    path('category/add/', AddCategoryView.as_view(), name='add_category'),
    path('payment/add/', AddPaymentView.as_view(), name='add_payment'),
    path('payment/delete/<int:pk>/', payment_delete, name='payment_delete'),
    path('categories/', ListCategory.as_view(), name='category_list'),
    path('category/delete/<int:pk>/', category_delete, name='category_delete'),

    path('earnings/', EarningsView.as_view(), name='earnings'),
    path('history/earn/<int:pk>/', EarningDetView.as_view(), name='earning_details'),
    path('earn/category/add/',AddEarningCategoryView.as_view(), name='add_earn_category'),
    path('earn/add/', AddEarningView.as_view(), name='add_earning'),
    path('earning/delete/<int:pk>/', earning_delete, name='earning_delete'),
    path('categories/earn/', ListEarnCategory.as_view(), name='earn_category_list'),
    path('category/earn/delete/<int:pk>/', earn_category_delete, name='earn_category_delete'),
]