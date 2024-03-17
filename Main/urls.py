from django.urls import path,include
from Main import views
app_name = "main"
urlpatterns = [
    path('',views.Index,name='index'),
]
