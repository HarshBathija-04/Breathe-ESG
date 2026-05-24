"""
Auth serializers for login, registration, and user management.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .authentication import generate_token

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')
        data['user'] = user
        return data


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return UserSerializer(obj['user']).data


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 
                  'role', 'tenant', 'tenant_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'full_name', 'tenant_name', 'created_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'role', 'tenant']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
