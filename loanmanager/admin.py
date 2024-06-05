from django.contrib import admin
from .models import CommentsRepliedTo, RedditUser, Loan, Payment, CurrencyConversion
# Register your models here.

admin.site.register(RedditUser)
admin.site.register(Loan)
admin.site.register(Payment)
admin.site.register(CommentsRepliedTo)
admin.site.register(CurrencyConversion)