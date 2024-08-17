from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Loan

def loan_list(request):
    username = request.GET.get('username', '')
    
    # Normalize the username by removing 'u/' or '/u/' prefix and stripping spaces
    if username.startswith('u/') or username.startswith('/u/'):
        username = username.split('/')[-1]
    
    loans = Loan.objects.all()

    # Filter loans by username (lender or borrower) using case-insensitive partial matching
    if username:
        loans = loans.filter(lender__username__icontains=username) | loans.filter(borrower__username__icontains=username)
    
    # Order loans by the creation date, descending
    loans = loans.order_by('-creation_date')

    # Paginate the loans
    paginator = Paginator(loans, 10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add latest payment record to each loan
    loans_with_payments = []
    for loan in page_obj:
        latest_payment = loan.payments.order_by('-payment_date').first()
        loans_with_payments.append({
            'loan': loan,
            'latest_payment': latest_payment
        })
    
    return render(request, 'loans.html', {'page_obj': page_obj})
