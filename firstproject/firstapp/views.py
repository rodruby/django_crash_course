from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views import View
from .forms import ReservationForm, ContactForm
from .models import Contact
from django.contrib import messages  # Add this import at the top
from pprint import pprint

# Create your views here.

#two types of views function and class based views

#example of function based view
def hello_world(request):
    return HttpResponse("Hello World from Function")

#example of a class based view
class HelloClass(View):
    def get(self, request):
        return HttpResponse("Hello World from Class")
    
def home(request):
    form = ReservationForm()
    if request.method == 'POST':
        print("POST data received")
        pprint(request.POST.dict())
        print('\n')

        form = ReservationForm(request.POST)
        
        if form.is_valid():
            form.save()
            return HttpResponse("Success")

    return render(request, 'firstapp/index.html', {'form': form})

def contact(request):
        
    if request.method == 'POST':
        print("POST data received")
        pprint(request.POST.dict())
        print('\n')

        form = ContactForm(request.POST)

        if form.is_valid():
            form.save()
            form = ContactForm()

            messages.success(request, "Contact form submitted successfully")
    else:
        form = ContactForm()
        messages.info(request, 'Welcome to the contact page!')
    
    return render(request, 'firstapp/contact.html', {'form': form})


def contact_list(request):
    contacts = Contact.objects.all().order_by('-created_at') #get all contacts

    return render(request, 'firstapp/contact_list.html', { 'contacts': contacts }) #Pass to template

def delete_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    try:        
        contact.delete()
        messages.success(request, 'Contact deleted successfully!')
        return redirect('contact_list')
    except:
        messages.error(request, 'Contact could not be deleted.')
        print(f"Record with {id} could not be deleted.")

    return render(request, 'firstapp/delete_contact.html', {'contact': contact})