from rest_framework import serializers
from .models import Loan, Payment, RedditUser


class RedditUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedditUser
        fields = '__all__'


class LoanSerializer(serializers.ModelSerializer):
    lender = serializers.SlugRelatedField(
        queryset=RedditUser.objects.all(),
        slug_field='username'
    )
    borrower = serializers.SlugRelatedField(
        queryset=RedditUser.objects.all(),
        slug_field='username'
    )

    class Meta:
        model = Loan
        fields = '__all__'  # include all fields or specify the fields you want

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
