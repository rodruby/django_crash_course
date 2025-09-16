from django.db import models

# Create your models here.

class MenuItem(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True) #model attributes
    price = models.IntegerField(null=True, blank=True)

class Reservation(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    guest_count = models.IntegerField(blank=True, null=True)
    reservation_time = models.DateField(auto_now=True)
    comments = models.CharField(max_length=1000)

class Contact(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)  
    subject = models.CharField(max_length=255, blank=True, null=True)  
    comments = models.CharField(max_length=1000)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
    class Meta:
        ordering = ['-created_at'] # newest