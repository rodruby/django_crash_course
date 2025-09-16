from django.urls import path
from . import views #importing the views


#list of urls
urlpatterns = [
    path('', views.home, name='home'),
    path('hello_function', views.hello_world),
    path('hello_class', views.HelloClass.as_view()),
    path('reservation', views.home, name="reservation"),  
    path('contact', views.contact, name="contact"), 
    path('contact/list', views.contact_list, name="contact_list"),
    path('contact/delete/<int:contact_id>', views.delete_contact, name="delete_contact")
]
