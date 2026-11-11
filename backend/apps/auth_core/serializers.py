"""
Auth serializers for login and user representation.
"""
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'role', 'tenant', 'tenant_name', 'is_active', 'created_at']
        read_only_fields = fields
