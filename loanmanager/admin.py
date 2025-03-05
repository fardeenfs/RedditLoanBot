from django.contrib import admin
from .models import CommentsRepliedTo, RedditUser, Loan, Payment, CurrencyConversion


class RedditUserAdmin(admin.ModelAdmin):
    list_filter = ('is_mod', 'is_active', 'has_unpaid_loan', 'is_banned')  # Filters for user status
    list_display = ('username', 'is_mod', 'is_active', 'has_unpaid_loan', 'is_banned')  # Columns in admin list view
    search_fields = ('username',)  # Search by username


class LoanAdmin(admin.ModelAdmin):
    list_filter = ('creation_date', 'is_confirmed', 'is_paid') 
    list_display = ('loan_id', 'lender', 'borrower', 'amount', 'currency', 'is_confirmed', 'is_paid') 
    search_fields = ('loan_id', 'lender__username', 'borrower__username') 


class PaymentAdmin(admin.ModelAdmin):
    list_filter = ('payment_date')  # Filter by currency and loan association
    list_display = ('payment_id_display', 'loan_id', 'loan', 'amount', 'currency', 'payment_date')  # Show loan ID in the list
    search_fields = ('loan__loan_id', 'loan__lender__username', 'loan__borrower__username')  # Search by loan ID or usernames

    def loan_id(self, obj):
        return obj.loan.loan_id  # Display loan ID in list
    loan_id.admin_order_field = 'loan__loan_id'  # Enable sorting by loan ID
    loan_id.short_description = 'Loan ID'  # Rename column header in admin


admin.site.register(RedditUser, RedditUserAdmin)
admin.site.register(Loan, LoanAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(CommentsRepliedTo)
admin.site.register(CurrencyConversion)

