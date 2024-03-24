# url.py
from django.urls import path,include
from Main import views
app_name = "main"
urlpatterns = [
    path('',views.Home,name='Home'),
    path('Submit',views.Submit,name='Submit'),
]
