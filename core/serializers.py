from rest_framework import serializers
from django.contrib.auth.models import AbstractUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=AbstractUser
        fields=['username','email','password','firstName','lastName','city','state','adress','is_superuser','is_staff']
        
        
        

