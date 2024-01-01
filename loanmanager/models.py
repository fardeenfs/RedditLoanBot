from django.db import models

class CommentsRepliedTo(models.Model):
    comment_reddit_id = models.CharField(max_length=1000, unique=True)

    def __str__(self):
        return f"{self.comment_reddit_id}"
    
    class Meta:
        verbose_name_plural = "Comments Replied To"

class RedditUser(models.Model):
    username = models.CharField(max_length=100, unique=True)

    borrower_pending_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    borrower_completed_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    borrower_pending_loan_count = models.IntegerField(default=0)
    borrower_completed_loan_count = models.IntegerField(default=0)
    borrower_repayment_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    lender_pending_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lender_completed_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lender_pending_loan_count = models.IntegerField(default=0)
    lender_completed_loan_count = models.IntegerField(default=0)

    is_mod = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    has_unpaid_loan = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"{self.username}"
    

class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    lender = models.ForeignKey(RedditUser, related_name='lent_loans', on_delete=models.CASCADE)
    borrower = models.ForeignKey(RedditUser, related_name='borrowed_loans', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    amount_in_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    is_unpaid = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    original_thread = models.URLField(max_length=1000, blank=True, null=True)
    thread_id = models.CharField(max_length=1000, blank=True, null=True)
    comment_id = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"{self.amount} {self.currency} from {self.lender} to {self.borrower}"

class Payment(models.Model):
    loan = models.ForeignKey(Loan, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.loan.borrower} repaid {self.loan.lender} {self.currency} {self.amount} towards Loan ID {self.loan.loan_id}"
