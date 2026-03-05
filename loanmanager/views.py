from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Loan, RedditUser
from django.db import models

@login_required
def notifications_home(request):
    pending_notifications = Loan.objects.filter(
        is_unpaid=True,
        is_cancelled=False,
        notification_dismissed=False
    ).select_related('lender', 'borrower').order_by('-creation_date')

    dismissed_notifications = Loan.objects.filter(
        is_unpaid=True,
        is_cancelled=False,
        notification_dismissed=True
    ).select_related('lender', 'borrower').order_by('-creation_date')

    return render(request, 'home.html', {
        'pending_notifications': pending_notifications,
        'dismissed_notifications': dismissed_notifications,
    })


@login_required
@require_POST
def dismiss_notification(request, loan_id):
    loan = get_object_or_404(Loan, loan_id=loan_id, is_unpaid=True, is_cancelled=False)
    loan.notification_dismissed = True
    loan.save(update_fields=['notification_dismissed'])
    return redirect('home')


@login_required
@require_POST
def undismiss_notification(request, loan_id):
    loan = get_object_or_404(Loan, loan_id=loan_id, is_unpaid=True, is_cancelled=False)
    loan.notification_dismissed = False
    loan.save(update_fields=['notification_dismissed'])
    return redirect('home')


def loan_list(request):
    username = request.GET.get('username', '')
    status = request.GET.get('status', '')
    currency = request.GET.get('currency', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Normalize the username by removing 'u/' or '/u/' prefix and stripping spaces
    if username.startswith('u/') or username.startswith('/u/'):
        username = username.split('/')[-1]

    loans = Loan.objects.all()

    # Filter loans by username (lender or borrower) using case-insensitive partial matching
    if username:
        loans = loans.filter(
            models.Q(lender__username__icontains=username) |
            models.Q(borrower__username__icontains=username)
        )

    # Filter by status
    if status:
        if status == 'paid':
            loans = loans.filter(is_paid=True)
        elif status == 'unpaid':
            loans = loans.filter(is_unpaid=True)
        elif status == 'pending':
            loans = loans.filter(is_paid=False, is_unpaid=False, is_cancelled=False)
        elif status == 'cancelled':
            loans = loans.filter(is_cancelled=True)
        elif status == 'confirmed':
            loans = loans.filter(is_confirmed=True)

    # Filter by currency
    if currency:
        loans = loans.filter(currency__iexact=currency)

    # Filter by amount range (in USD)
    if min_amount:
        try:
            loans = loans.filter(amount_in_usd__gte=float(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            loans = loans.filter(amount_in_usd__lte=float(max_amount))
        except ValueError:
            pass

    # Filter by date range
    if start_date:
        try:
            loans = loans.filter(creation_date__gte=start_date)
        except ValueError:
            pass

    if end_date:
        try:
            loans = loans.filter(creation_date__lte=end_date)
        except ValueError:
            pass

    # Order loans by the creation date, descending
    loans = loans.order_by('-creation_date')

    # Paginate the loans
    paginator = Paginator(loans, 10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'username': username,
        'status': status,
        'currency': currency,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'loans.html', context)


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


def loan_detail(request, loan_id):
    loan = get_object_or_404(Loan, loan_id=loan_id)
    payments = loan.payments.filter(is_cancelled=False).order_by('-payment_date')

    context = {
        'loan': loan,
        'payments': payments,
    }
    return render(request, 'loan_detail.html', context)

