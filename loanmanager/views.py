from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Loan, RedditUser
from django.db import models

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


def reddit_user_detail(request, username):
    user = get_object_or_404(RedditUser, username=username)

    borrowed_list = user.borrowed_loans.select_related('lender').order_by('-creation_date')
    lent_list = user.lent_loans.select_related('borrower').order_by('-creation_date')

    borrowed_paginator = Paginator(borrowed_list, 10)
    lent_paginator = Paginator(lent_list, 10)

    borrowed_page_number = request.GET.get('borrowed_page')
    lent_page_number = request.GET.get('lent_page')

    borrowed_loans = borrowed_paginator.get_page(borrowed_page_number)
    lent_loans = lent_paginator.get_page(lent_page_number)

    context = {
        'user': user,
        'borrowed_loans': borrowed_loans,
        'lent_loans': lent_loans,
    }
    return render(request, 'user_detail.html', context)


def search_users(request):
    query = request.GET.get('q', '').strip()

    # Remove 'u/' prefix if present
    if query.lower().startswith('u/'):
        query = query[2:]

    if query:
        users = RedditUser.objects.filter(username__icontains=query)

        # Manually calculate total_loans for each user
        for user in users:
            user.total_loans = (
                user.borrower_pending_loan_count + 
                user.borrower_completed_loan_count + 
                user.lender_pending_loan_count + 
                user.lender_completed_loan_count
            )
            user.pending_loans = (
                user.borrower_pending_loan_count + 
                user.lender_pending_loan_count
            )
            user.completed_loans = (
                user.borrower_completed_loan_count +
                user.lender_completed_loan_count
            )

        # Order users by total_loans (in descending order)
        users = sorted(users, key=lambda user: user.total_loans, reverse=True)
    else:
        users = RedditUser.objects.none()

    context = {
        'query': query,
        'users': users,
    }

    return render(request, 'search.html', context)

