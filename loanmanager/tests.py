import sys
from decimal import Decimal
from unittest import skipIf
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import CommentsRepliedTo, Loan, Payment, RedditUser, CurrencyConversion
from .api import get_loan_url_disclaimer

# Django's test client has a context copy bug on Python 3.14+
PY314_SKIP = skipIf(sys.version_info >= (3, 14), "Django template context copy bug on Python 3.14+")


class GetLoanUrlDisclaimerTests(TestCase):
    """Tests for the get_loan_url_disclaimer helper function."""

    def test_with_integer_id(self):
        result = get_loan_url_disclaimer(42)
        self.assertIn("/loan/42/", result)
        self.assertIn("simpleloans.live", result)

    def test_with_loan_object(self):
        lender = RedditUser.objects.create(username="lender1")
        borrower = RedditUser.objects.create(username="borrower1")
        loan = Loan.objects.create(
            lender=lender, borrower=borrower,
            amount=100, currency="USD", amount_in_usd=100
        )
        result = get_loan_url_disclaimer(loan)
        self.assertIn(f"/loan/{loan.loan_id}/", result)

    def test_with_string_id(self):
        result = get_loan_url_disclaimer("99")
        self.assertIn("/loan/99/", result)


@PY314_SKIP
class LoanListViewTests(TestCase):
    """Tests for the loan_list web view."""

    def setUp(self):
        self.client = Client()
        self.lender = RedditUser.objects.create(username="test_lender")
        self.borrower = RedditUser.objects.create(username="test_borrower")
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=500, currency="USD", amount_in_usd=500
        )

    def test_loan_list_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_filter_by_username(self):
        response = self.client.get("/", {"username": "test_lender"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_username_with_u_prefix(self):
        response = self.client.get("/", {"username": "u/test_lender"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_status_paid(self):
        self.loan.is_paid = True
        self.loan.save()
        response = self.client.get("/", {"status": "paid"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_status_pending(self):
        response = self.client.get("/", {"status": "pending"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_currency(self):
        response = self.client.get("/", {"currency": "USD"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_min_amount(self):
        response = self.client.get("/", {"min_amount": "100"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_max_amount(self):
        response = self.client.get("/", {"max_amount": "1000"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test_lender")

    def test_filter_by_amount_excludes(self):
        response = self.client.get("/", {"min_amount": "1000"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "test_lender")

    def test_filter_invalid_amount_ignored(self):
        response = self.client.get("/", {"min_amount": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_no_results(self):
        response = self.client.get("/", {"username": "nonexistent_user_xyz"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No loans found")


@PY314_SKIP
class UserDetailViewTests(TestCase):
    """Tests for the reddit_user_detail web view."""

    def setUp(self):
        self.client = Client()
        self.user = RedditUser.objects.create(username="detail_user")

    def test_user_detail_loads(self):
        response = self.client.get(f"/user/{self.user.username}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "detail_user")

    def test_user_detail_404(self):
        response = self.client.get("/user/nonexistent_user_xyz/")
        self.assertEqual(response.status_code, 404)


@PY314_SKIP
class LoanDetailViewTests(TestCase):
    """Tests for the loan_detail web view."""

    def setUp(self):
        self.client = Client()
        self.lender = RedditUser.objects.create(username="lender_detail")
        self.borrower = RedditUser.objects.create(username="borrower_detail")
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=250, currency="EUR", amount_in_usd=275
        )

    def test_loan_detail_loads(self):
        response = self.client.get(f"/loan/{self.loan.loan_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "250")
        self.assertContains(response, "EUR")

    def test_loan_detail_404(self):
        response = self.client.get("/loan/999999/")
        self.assertEqual(response.status_code, 404)


@PY314_SKIP
class SearchUsersViewTests(TestCase):
    """Tests for the search_users web view."""

    def setUp(self):
        self.client = Client()
        self.user = RedditUser.objects.create(username="searchable_user")

    def test_search_page_loads(self):
        response = self.client.get("/user/")
        self.assertEqual(response.status_code, 200)

    def test_search_finds_user(self):
        response = self.client.get("/user/", {"q": "searchable"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "searchable_user")

    def test_search_with_u_prefix(self):
        response = self.client.get("/user/", {"q": "u/searchable"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "searchable_user")


class APIAuthMixin:
    """Mixin to set up authenticated API client."""

    def setUp(self):
        self.api_client = APIClient()
        self.user = User.objects.create_user(username="apiuser", password="testpass123")
        self.api_client.force_authenticate(user=self.user)

        self.lender = RedditUser.objects.create(username="api_lender")
        self.borrower = RedditUser.objects.create(username="api_borrower")


class ConfirmLoanByThreadAPITests(APIAuthMixin, TestCase):
    """Tests for ConfirmLoanByThreadView."""

    def setUp(self):
        super().setUp()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
            thread_id="thread123"
        )

    def test_confirm_loan_success(self):
        response = self.api_client.post("/api/confirm-loan-by-thread/", {
            "author": "api_borrower",
            "comment_id": "comment_confirm_1",
            "thread_id": "thread123",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_confirmed)

    def test_confirm_loan_no_loan_found(self):
        response = self.api_client.post("/api/confirm-loan-by-thread/", {
            "author": "api_borrower",
            "comment_id": "comment_confirm_2",
            "thread_id": "nonexistent_thread",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("No unconfirmed loan found", response.data["message"])

    def test_duplicate_comment_rejected(self):
        CommentsRepliedTo.objects.create(comment_reddit_id="dupe_comment")
        response = self.api_client.post("/api/confirm-loan-by-thread/", {
            "author": "api_borrower",
            "comment_id": "dupe_comment",
            "thread_id": "thread123",
        })
        self.assertEqual(response.status_code, 400)


class ConfirmLoanWithIDAPITests(APIAuthMixin, TestCase):
    """Tests for ConfirmLoanWithIDView."""

    def setUp(self):
        super().setUp()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=200, currency="USD", amount_in_usd=200,
        )

    def test_confirm_by_borrower(self):
        response = self.api_client.post("/api/confirm-loan-with-id/", {
            "author": "api_borrower",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cid_1",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_confirmed)

    def test_confirm_by_wrong_user(self):
        response = self.api_client.post("/api/confirm-loan-with-id/", {
            "author": "api_lender",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cid_2",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("not the borrower", response.data["message"])

    def test_confirm_by_mod(self):
        mod = RedditUser.objects.create(username="mod_user", is_mod=True)
        response = self.api_client.post("/api/confirm-loan-with-id/", {
            "author": "mod_user",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cid_3",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_confirmed)
        self.assertIn("Moderator", response.data["message"])

    def test_confirm_already_confirmed(self):
        self.loan.is_confirmed = True
        self.loan.save()
        response = self.api_client.post("/api/confirm-loan-with-id/", {
            "author": "api_borrower",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cid_4",
        })
        self.assertEqual(response.status_code, 400)


class PayLoanByThreadAPITests(APIAuthMixin, TestCase):
    """Tests for PayLoanByThreadView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_pending_loan_balance = 100
        self.lender.lender_pending_loan_count = 1
        self.lender.save()
        self.borrower.borrower_pending_loan_balance = 100
        self.borrower.borrower_pending_loan_count = 1
        self.borrower.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
            thread_id="pay_thread"
        )

    def test_pay_loan_success(self):
        response = self.api_client.post("/api/pay-loan-by-thread/", {
            "author": "api_lender",
            "amount": "100",
            "currency": "USD",
            "comment_id": "comment_pay_1",
            "thread_id": "pay_thread",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_paid)
        self.assertIn("simpleloans.live", response.data["message"])

    def test_pay_loan_no_loan_found(self):
        response = self.api_client.post("/api/pay-loan-by-thread/", {
            "author": "api_lender",
            "amount": "100",
            "currency": "USD",
            "comment_id": "comment_pay_2",
            "thread_id": "nonexistent",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("No active loan found", response.data["message"])


class PayLoanWithIDAPITests(APIAuthMixin, TestCase):
    """Tests for PayLoanWithIDView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_pending_loan_balance = 100
        self.lender.lender_pending_loan_count = 1
        self.lender.save()
        self.borrower.borrower_pending_loan_balance = 100
        self.borrower.borrower_pending_loan_count = 1
        self.borrower.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
        )

    def test_pay_by_lender(self):
        response = self.api_client.post("/api/pay-loan-with-id/", {
            "author": "api_lender",
            "loan_id": self.loan.loan_id,
            "amount": "100",
            "currency": "USD",
            "comment_id": "comment_pwid_1",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_paid)

    def test_pay_by_wrong_user(self):
        response = self.api_client.post("/api/pay-loan-with-id/", {
            "author": "api_borrower",
            "loan_id": self.loan.loan_id,
            "amount": "100",
            "currency": "USD",
            "comment_id": "comment_pwid_2",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("not the lender", response.data["message"])


class UnpaidLoanByThreadAPITests(APIAuthMixin, TestCase):
    """Tests for UnpaidLoanByThreadView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_pending_loan_balance = 100
        self.lender.lender_pending_loan_count = 1
        self.lender.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
            thread_id="unpaid_thread"
        )

    def test_unpaid_success(self):
        response = self.api_client.post("/api/unpaid-loan-by-thread/", {
            "author": "api_lender",
            "comment_id": "comment_unpaid_1",
            "thread_id": "unpaid_thread",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_unpaid)


class CancelLoanByThreadAPITests(APIAuthMixin, TestCase):
    """Tests for CancelLoanByThreadView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_pending_loan_balance = 100
        self.lender.lender_pending_loan_count = 1
        self.lender.save()
        self.borrower.borrower_pending_loan_balance = 100
        self.borrower.borrower_pending_loan_count = 1
        self.borrower.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
            thread_id="cancel_thread"
        )

    def test_cancel_success(self):
        response = self.api_client.post("/api/cancel-loan-by-thread/", {
            "author": "api_lender",
            "comment_id": "comment_cancel_1",
            "thread_id": "cancel_thread",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_cancelled)

    def test_cancel_no_loan_found(self):
        response = self.api_client.post("/api/cancel-loan-by-thread/", {
            "author": "api_lender",
            "comment_id": "comment_cancel_2",
            "thread_id": "nonexistent",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("No active loan found", response.data["message"])


class CancelLoanWithIDAPITests(APIAuthMixin, TestCase):
    """Tests for CancelLoanWithIDView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_pending_loan_balance = 100
        self.lender.lender_pending_loan_count = 1
        self.lender.save()
        self.borrower.borrower_pending_loan_balance = 100
        self.borrower.borrower_pending_loan_count = 1
        self.borrower.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
        )

    def test_cancel_by_lender(self):
        response = self.api_client.post("/api/cancel-loan-with-id/", {
            "author": "api_lender",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cwid_1",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_cancelled)

    def test_cancel_by_wrong_user(self):
        response = self.api_client.post("/api/cancel-loan-with-id/", {
            "author": "api_borrower",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cwid_2",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("not the lender", response.data["message"])

    def test_cancel_by_mod(self):
        mod = RedditUser.objects.create(username="mod_cancel", is_mod=True)
        response = self.api_client.post("/api/cancel-loan-with-id/", {
            "author": "mod_cancel",
            "loan_id": self.loan.loan_id,
            "comment_id": "comment_cwid_3",
        })
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_cancelled)
        self.assertIn("Moderator", response.data["message"])


class CancelPaymentAPITests(APIAuthMixin, TestCase):
    """Tests for CancelPaymentView."""

    def setUp(self):
        super().setUp()
        self.lender.lender_completed_loan_balance = 100
        self.lender.lender_completed_loan_count = 1
        self.lender.save()
        self.borrower.borrower_completed_loan_balance = 100
        self.borrower.borrower_completed_loan_count = 1
        self.borrower.borrower_repayment_total = 100
        self.borrower.save()
        self.loan = Loan.objects.create(
            lender=self.lender, borrower=self.borrower,
            amount=100, currency="USD", amount_in_usd=100,
            is_paid=True
        )
        self.payment = Payment.objects.create(
            loan=self.loan, amount=100, currency="USD"
        )

    def test_cancel_payment_success(self):
        response = self.api_client.post("/api/cancel-payment-with-id/", {
            "author": "api_lender",
            "payment_id": f"P{self.payment.id}",
            "comment_id": "comment_cp_1",
        })
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_cancelled)

    def test_cancel_payment_wrong_user(self):
        response = self.api_client.post("/api/cancel-payment-with-id/", {
            "author": "api_borrower",
            "payment_id": f"P{self.payment.id}",
            "comment_id": "comment_cp_2",
        })
        self.assertEqual(response.status_code, 403)


class TrackCommentAPITests(APIAuthMixin, TestCase):
    """Tests for TrackCommentView."""

    def test_track_new_comment(self):
        response = self.api_client.post("/api/track-comment/", {
            "comment_id": "track_1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CommentsRepliedTo.objects.filter(comment_reddit_id="track_1").exists())

    def test_track_duplicate_comment(self):
        CommentsRepliedTo.objects.create(comment_reddit_id="track_dupe")
        response = self.api_client.post("/api/track-comment/", {
            "comment_id": "track_dupe",
        })
        self.assertEqual(response.status_code, 400)


class UnauthenticatedAPITests(TestCase):
    """Tests that API endpoints require authentication."""

    def setUp(self):
        self.api_client = APIClient()

    def test_confirm_requires_auth(self):
        response = self.api_client.post("/api/confirm-loan-by-thread/", {})
        self.assertEqual(response.status_code, 401)

    def test_pay_requires_auth(self):
        response = self.api_client.post("/api/pay-loan-by-thread/", {})
        self.assertEqual(response.status_code, 401)

    def test_cancel_requires_auth(self):
        response = self.api_client.post("/api/cancel-loan-by-thread/", {})
        self.assertEqual(response.status_code, 401)

    def test_track_comment_requires_auth(self):
        response = self.api_client.post("/api/track-comment/", {})
        self.assertEqual(response.status_code, 401)
