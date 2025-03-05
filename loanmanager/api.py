import copy
import decimal
import math
from rest_framework import viewsets
from rest_framework.views import APIView

from loanmanager.helper_funcs import convert_currency, generate_markdown_table, reduce_to_latest_5_loans
from .models import CommentsRepliedTo, Loan, Payment, RedditUser
from .serializers import LoanSerializer, PaymentSerializer
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

def check_if_comment_has_been_replied_to(comment_id):
    # Check if comment has been replied to
    if CommentsRepliedTo.objects.filter(comment_reddit_id=comment_id).count() > 0:
        return True
    return False


class TrackCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])
            return Response({'message': f'''Noted!'''}, status=status.HTTP_200_OK)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Loan.objects.all()
        lender = self.request.query_params.get('lender', None)
        borrower = self.request.query_params.get('borrower', None)
        if lender is not None:
            queryset = queryset.filter(lender__username=lender)
        if borrower is not None:
            queryset = queryset.filter(borrower__username=borrower)
        return queryset
    
    def create(self, request, *args, **kwargs):

        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        # Check if lender and borrower are in RedditUser table. If not, create them. Get the user objects. Replace the username strings with the user objects.
        lender_username = self.request.data['lender']
        borrower_username = self.request.data['borrower']
        lender_obj, _ = RedditUser.objects.get_or_create(username=lender_username)
        borrower_obj, _ = RedditUser.objects.get_or_create(username=borrower_username)

        outstanding_borrowed_loans = Loan.objects.filter(borrower=lender_obj, is_paid=False, is_cancelled=False)

        if lender_obj.username == borrower_obj.username:
                return Response({'message': f'''You cannot lend to yourself!'''}, status=status.HTTP_200_OK)

        if len(outstanding_borrowed_loans) > 0:
            return Response({'message': f'''You are not allowed to lend at this time. You have one or more outstanding loan(s) where you are the borrower. 
You cannot be a lender and borrower at the same time! \n\n
You can lend again once you have paid these loans. Use the $check command to see the details of these loans. \n\n If the loan has been paid, but the lender has not
marked it as 'paid', request them to do so or contact the mods. '''}, status=status.HTTP_200_OK)
        
        try:
            data = copy.deepcopy(request.data)


            # Update request data with RedditUser instances
            data['lender'] = lender_obj
            data['borrower'] = borrower_obj
            data['currency'] = data['currency'].upper()
            data['amount'] = decimal.Decimal(data['amount'])

            # TODO: If currency is not USD, convert amount to USD
            try:
                if data['currency'] != 'USD':
                    print('Converting currency to ', data['currency'])
                    converted_amount = convert_currency(data['amount'], data['currency'])
                    print('Converted amount: ', converted_amount)

                    if converted_amount is not None:
                        data['amount_in_usd'] = converted_amount
                    else:
                        print('Currency conversion failed. Using USD as default')
                        data['currency'] = 'USD'
                        data['amount_in_usd'] = data['amount']                               
                else:
                    data['amount_in_usd'] = data['amount']
            except:
                print('Currency conversion failed. Using USD as default')
                data['currency'] = 'USD'
                data['amount_in_usd'] = data['amount']


            # Proceed with normal creation process
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance += decimal.Decimal(data['amount_in_usd'])
            lender_obj.lender_pending_loan_count += 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance += decimal.Decimal(data['amount_in_usd'])
            borrower_obj.borrower_pending_loan_count += 1
            borrower_obj.save()

            return Response({
                'message': 
f'''Noted! I will remember that /u/{lender_obj.username} lent {data['amount']} {data['currency'].upper()} to /u/{borrower_obj.username}! \n\n
**Note**: This does not confirm that the borrower has received the money, but it does confirm that the lender has agreed to lend the money.
The loan ID is `{serializer.data['loan_id']}`. \n\n
The borrower can confirm that they received the money for the loan with the following command: \n\n
`$confirm_with_id {serializer.data['loan_id']}` or just `$confirm` (if used on this thread)\n\n
The lender can mark this loan as paid with the following command: \n\n
`$paid_with_id {serializer.data['loan_id']} [AMOUNT] [CURRENCY]` or just `$paid [AMOUNT] [CURRENCY]` (if used on this thread)\n\n
If the loan has been cancelled or refunded, the lender can cancel the loan with the following command: \n\n
`$cancel_with_id {serializer.data['loan_id']}` or just `$cancel` (if used on this thread)\n\n
If the borrower has not repaid the loan, the lender can mark the loan as unpaid with the following command: \n\n
`$unpaid_with_id {serializer.data['loan_id']}` or just `$unpaid` (if used on this thread)\n\n'''
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            print(e)
            return Response({'message': f'''I couldn't understand that. Please recheck your loan command syntax. \n\n A valid request looks like this
\n\n `$loan [AMOUNT] [CURRENCY]` \n\n For example: `$loan 100 USD`'''}, status=status.HTTP_200_OK)


class ConfirmLoanByThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            author = self.request.data['author']
            loan_obj = Loan.objects.filter(thread_id=self.request.data['thread_id'], borrower__username=author, is_confirmed=False, is_cancelled=False)
            if loan_obj.count() > 1:
                return Response({'message': f'''Multiple loans found on this thread! Please use `$confirm_with_id` command instead.'''}, status=status.HTTP_200_OK)
            elif loan_obj.count() == 0:
                raise Loan.DoesNotExist
            
            loan_obj = loan_obj[0]
            loan_obj.is_confirmed = True
            loan_obj.save()
            return Response({'message': f'''I have noted that down! \n\n u/{loan_obj.borrower.username} has confirmed that they have received {loan_obj.amount} {loan_obj.currency} from 
                            u/{loan_obj.lender.username} and the loan is thus confirmed. (Loan ID `{loan_obj.loan_id}`: `Confirmed`)'''}, status=status.HTTP_200_OK)
        
        except Loan.DoesNotExist:
            return Response({'message': f'''No unconfirmed loan found! Please ensure that the lender has used the `$loan` command and the comment has been responded
                              to by the bot.\n\n If the loan was cancelled/refunded previously, request the lender to use the `$loan` command again'''}, status=status.HTTP_200_OK)
        

class ConfirmLoanWithIDView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            loan_obj = Loan.objects.get(loan_id=self.request.data['loan_id'], is_cancelled=False)
            author = self.request.data['author']
            author_obj, _ = RedditUser.objects.get_or_create(username=author)
            if loan_obj.borrower.username != author_obj.username and not author_obj.is_mod:
                return Response({'message': f'''You are not the borrower of this loan. You cannot 'confirm' this loan. If this is an error, please contact 
                                a moderator.'''}, status=status.HTTP_200_OK) 
            if loan_obj.is_confirmed:
                return Response({'message': f'''This loan has already been confirmed!'''}, status=status.HTTP_400_BAD_REQUEST)
            
            loan_obj.is_confirmed = True
            loan_obj.save()
            if loan_obj.borrower.username == author_obj.username:
                return Response({'message': f'''I have noted that down! \n\n u/{loan_obj.borrower.username} has confirmed that they have received {loan_obj.amount} {loan_obj.currency} from 
                            u/{loan_obj.lender.username} and the loan is thus marked as confirmed. (Loan ID `{loan_obj.loan_id}`: `Confirmed`)'''}, status=status.HTTP_200_OK)
            elif author_obj.is_mod:
                return Response({'message': f'''**Moderator Command** \n\n I have noted that down! \n\n The moderator u/{author_obj.username} has confirmed that u/{loan_obj.borrower.username} has received {loan_obj.amount} {loan_obj.currency} from 
                            u/{loan_obj.lender.username} and the loan is thus marked as confirmed. (Loan ID `{loan_obj.loan_id}`: `Confirmed`)'''}, status=status.HTTP_200_OK)
        except Loan.DoesNotExist:
            return Response({'message': f'''No active loan found! Please ensure that the lender has used the `$loan` command and the comment has been responded
                              to by the bot.\n\n If the loan was cancelled/refunded previously, request the lender to use the `$loan` command again'''}, status=status.HTTP_200_OK)
        

class PayLoanByThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            author = self.request.data['author']
            amount = self.request.data['amount']
            currency = self.request.data['currency']

            loan_obj = Loan.objects.filter(thread_id=self.request.data['thread_id'], lender__username=author, is_paid=False, is_cancelled=False)
            if loan_obj.count() > 1:
                return Response({'message': f'''Multiple loans found on this thread! Please use `$paid_with_id` command instead.'''}, status=status.HTTP_200_OK)
            elif loan_obj.count() == 0:
                raise Loan.DoesNotExist

            loan_obj = loan_obj[0]
            loan_obj.is_unpaid = False
            loan_obj.is_paid = True
            loan_obj.save()
            
            if amount != '':
                amount = decimal.Decimal(amount)
            else:
                amount = loan_obj.amount 
            if currency != '':
                currency = currency.upper()
            else:
                currency = loan_obj.currency
                
            Payment.objects.get_or_create(loan=loan_obj, amount=amount, currency=currency)

            lender_obj = loan_obj.lender
            borrower_obj = loan_obj.borrower


            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.lender_completed_loan_balance += loan_obj.amount_in_usd
            lender_obj.lender_completed_loan_count += 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance -= loan_obj.amount_in_usd
            borrower_obj.borrower_pending_loan_count -= 1
            borrower_obj.borrower_completed_loan_balance += loan_obj.amount_in_usd
            borrower_obj.borrower_completed_loan_count += 1
            borrower_obj.borrower_repayment_total += loan_obj.amount_in_usd
            borrower_obj.save()

            return Response({'message': f'''That's sweet! I will note that down. \n\n u/{loan_obj.lender.username} has confirmed that they have received {amount} {currency} from 
                            u/{loan_obj.borrower.username} and the loan is thus marked as paid. (Loan ID `{loan_obj.loan_id}`: `Paid`)'''}, status=status.HTTP_200_OK)
        
        except Loan.DoesNotExist:
            return Response({'message': 
                             f'''No active loan found! Please ensure that the lender has used the `$loan` command and the comment has been responded
to by the bot. \n\n Remember only the 'lender' of the loan can mark it as paid. \n\n If the loan was cancelled/refunded previously,
request the lender to use the `$loan` command again.'''}, status=status.HTTP_200_OK)

    
class PayLoanWithIDView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            print(self.request.data)
            loan_obj = Loan.objects.get(loan_id=self.request.data['loan_id'], is_cancelled=False)
            author = self.request.data['author']
            amount = self.request.data['amount']
            currency = self.request.data['currency']
            author_obj, _ = RedditUser.objects.get_or_create(username=author)
            if loan_obj.lender.username != author_obj.username and not author_obj.is_mod:
                return Response({'message': f'''You are not the lender of this loan. You cannot mark this loan as paid. If this is an error, please contact 
                                a moderator.\n\n The lender of the loan is currently u/{loan_obj.lender.username}'''}, status=status.HTTP_200_OK)   
            if loan_obj.is_paid:
                return Response({'message': f'''This loan has already been paid!'''}, status=status.HTTP_400_BAD_REQUEST)
            loan_obj.is_unpaid = False
            loan_obj.is_paid = True
            loan_obj.save()

            print('Amount: ', amount)
            print('Currency: ', currency)
            if amount != '':
                amount = decimal.Decimal(amount)
            else:
                amount = loan_obj.amount 
            if currency != '':
                currency = currency.upper()
            else:
                currency = loan_obj.currency

            Payment.objects.get_or_create(loan=loan_obj, amount=amount, currency=currency)

            
            lender_obj = loan_obj.lender
            borrower_obj = loan_obj.borrower


            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.lender_completed_loan_balance += loan_obj.amount_in_usd
            lender_obj.lender_completed_loan_count += 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance -= loan_obj.amount_in_usd
            borrower_obj.borrower_pending_loan_count -= 1
            borrower_obj.borrower_completed_loan_balance += loan_obj.amount_in_usd
            borrower_obj.borrower_completed_loan_count += 1
            borrower_obj.borrower_repayment_total += loan_obj.amount_in_usd
            borrower_obj.save()

            if loan_obj.lender.username == author_obj.username:
                return Response({'message': f'''That's sweet! I will note that down. \n\n u/{loan_obj.lender.username} has confirmed that they have received {amount} {currency} 
                            from u/{loan_obj.borrower.username} and the loan is thus marked as paid. (Loan ID `{loan_obj.loan_id}`: `Paid`)'''}, status=status.HTTP_200_OK)
            elif author_obj.is_mod:
                return Response({'message': f'''**Moderator Command** \n\n That's sweet! I will note that down. \n\n The moderator u/{author_obj.username} has confirmed that u/{loan_obj.lender.username} has received {amount} {currency} 
                            from u/{loan_obj.borrower.username} and the loan is thus marked as paid. (Loan ID `{loan_obj.loan_id}`: `Paid`)'''}, status=status.HTTP_200_OK)
    
        except Loan.DoesNotExist:
            return Response({'message': f'''No active loan found! Please ensure that the `$loan` command was used and the comment has been responded
                              to by the bot.\n\n If the loan was cancelled/refunded previously, request the lender to use the `$loan` command again'''}, status=status.HTTP_200_OK)


class UnpaidLoanByThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            author = self.request.data['author']

            loan_obj = Loan.objects.filter(thread_id=self.request.data['thread_id'], lender__username=author, is_paid=False, is_cancelled=False)
            if loan_obj.count() > 1:
                return Response({'message': f'''Multiple loans found on this thread! Please use `$unpaid_with_id` command instead.'''}, status=status.HTTP_200_OK)
            elif loan_obj.count() == 0:
                raise Loan.DoesNotExist
            
            loan_obj = loan_obj[0]

            loan_obj.is_unpaid = True
            loan_obj.borrower.has_unpaid_loan = True
            loan_obj.save()

            lender_obj = loan_obj.lender

             # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.lender_unpaid_loan_balance += loan_obj.amount_in_usd
            lender_obj.lender_unpaid_loan_count += 1
            lender_obj.save()

            return Response({'message': f'''That's unfortunate! \n\n u/{loan_obj.lender.username} has confirmed that they have not received a repayment for the [loan]({loan_obj}) from 
                            u/{loan_obj.borrower.username} and the loan is thus marked as unpaid. \n\n The mods will be notified automatically! (Loan ID `{loan_obj.loan_id}`: `Unpaid`)'''}, status=status.HTTP_200_OK)
        
        except Loan.DoesNotExist:
            return Response({'message': f'''No active loan found! Please ensure that the lender has used the `$loan` command and the comment has been responded
to by the bot. \n\n Remember only the 'lender' of the loan can mark it as unpaid.\n\n If the loan was cancelled/refunded previously, 
request the lender to use the `$loan` command again'''}, status=status.HTTP_200_OK)


class UnpaidLoanWithIDView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            print(self.request.data)
            loan_obj = Loan.objects.get(loan_id=self.request.data['loan_id'], is_cancelled=False)
            author = self.request.data['author']
            author_obj, _ = RedditUser.objects.get_or_create(username=author)
            if loan_obj.lender.username != author_obj.username and not author_obj.is_mod:
                return Response({'message': f'''You are not the lender of this loan. You cannot mark this loan as unpaid. If this is an error, please contact 
                                a moderator.\n\n The lender of the loan is currently u/{loan_obj.lender.username}'''}, status=status.HTTP_200_OK)   
            if loan_obj.is_unpaid:
                return Response({'message': f'''This loan has already been marked as unpaid!'''}, status=status.HTTP_400_BAD_REQUEST)
            loan_obj.is_unpaid = True
            loan_obj.save()

            borrower_obj = loan_obj.borrower
            borrower_obj.has_unpaid_loan = True
            borrower_obj.save()

            lender_obj = loan_obj.lender

            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.lender_unpaid_loan_balance += loan_obj.amount_in_usd
            lender_obj.lender_unpaid_loan_count += 1
            lender_obj.save()

            if loan_obj.lender.username == author_obj.username:
                return Response({'message': f'''That's unfortunate! \n\n u/{loan_obj.lender.username} has confirmed that they have not received a repayment for the [loan]({loan_obj}) from 
                            u/{loan_obj.borrower.username} and the loan is thus marked as unpaid. \n\n The mods will be notified automatically! (Loan ID `{loan_obj.loan_id}`: `Unpaid`)'''}, status=status.HTTP_200_OK)
            elif author_obj.is_mod:
                return Response({'message': f'''**Moderator Command** \n\n That's unfortunate! \n\n The moderator u/{author_obj.username} has confirmed that u/{loan_obj.lender.username} has not received a repayment for the `loan {loan_obj.loan_id})` from 
                            u/{loan_obj.borrower.username} and the loan is thus marked as unpaid. \n\n (Loan ID `{loan_obj.loan_id}`: `Unpaid`)'''}, status=status.HTTP_200_OK)
        
        except Loan.DoesNotExist:
            return Response({'message': f'''No active loan found! Please ensure that the `$loan` command was used and the comment has been responded
to by the bot. \n\n Remember only the 'lender' of the loan can mark it as unpaid. \n\n If the loan was cancelled/refunded previously, 
request the lender to use the `$loan` command again'''}, status=status.HTTP_200_OK)


# Return all loans and payments for a given user.
class CheckUserLoansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This loan has already been recorded!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            username = self.request.data['username']
            try:
                user_obj = RedditUser.objects.get(username__iexact=username)
            except:
                user_obj,_ = RedditUser.objects.get_or_create(username=username)
                
            lend_out_records = Loan.objects.filter(lender=user_obj, is_paid=False, is_cancelled=False).order_by('-creation_date')[:5]
            borrowed_records = Loan.objects.filter(borrower=user_obj, is_paid=False, is_cancelled=False).order_by('-creation_date')[:5]
            
            lend_out_payments = Payment.objects.filter(loan__lender=user_obj).order_by('-payment_date')[:5]
            borrowed_payments = Payment.objects.filter(loan__borrower=user_obj).order_by('-payment_date')[:5]
            
            records = []
            for rec in lend_out_records:
                record = {}
                record['loan_id'] = rec.loan_id
                record['lender'] = rec.lender.username
                record['borrower'] = rec.borrower.username
                record['amount'] = rec.amount
                record['currency'] = rec.currency
                record['repaid'] = decimal.Decimal(0)
                record['repayment_currency'] = rec.currency
                record['confirmed'] = rec.is_confirmed
                record['paid'] = rec.is_paid
                record['unpaid'] = rec.is_unpaid
                record['loan_thread'] = rec.original_thread
                record['date_created'] = rec.creation_date
                record['date_repayment'] = None
                records.append(record)

            for rec in borrowed_records:
                record = {}
                record['loan_id'] = rec.loan_id
                record['lender'] = rec.lender.username
                record['borrower'] = rec.borrower.username
                record['amount'] = rec.amount
                record['currency'] = rec.currency
                record['repaid'] = decimal.Decimal(0)
                record['repayment_currency'] = rec.currency
                record['confirmed'] = rec.is_confirmed
                record['paid'] = rec.is_paid
                record['unpaid'] = rec.is_unpaid
                record['loan_thread'] = rec.original_thread
                record['date_created'] = rec.creation_date
                record['date_repayment'] = None
                records.append(record)
            
            for rec in lend_out_payments:
                record = {}
                record['loan_id'] = rec.loan.loan_id
                record['lender'] = rec.loan.lender.username
                record['borrower'] = rec.loan.borrower.username
                record['amount'] = rec.loan.amount
                record['currency'] = rec.loan.currency
                record['repaid'] = rec.amount
                record['repayment_currency'] = rec.currency
                record['confirmed'] = rec.loan.is_confirmed
                record['paid'] = rec.loan.is_paid
                record['unpaid'] = rec.loan.is_unpaid
                record['loan_thread'] = rec.loan.original_thread
                record['date_created'] = rec.loan.creation_date
                record['date_repayment'] = rec.payment_date
                records.append(record)

            for rec in borrowed_payments:
                record = {}
                record['loan_id'] = rec.loan.loan_id
                record['lender'] = rec.loan.lender.username
                record['borrower'] = rec.loan.borrower.username
                record['amount'] = rec.loan.amount
                record['currency'] = rec.loan.currency
                record['repaid'] = rec.amount
                record['repayment_currency'] = rec.currency
                record['confirmed'] = rec.loan.is_confirmed
                record['paid'] = rec.loan.is_paid
                record['unpaid'] = rec.loan.is_unpaid
                record['loan_thread'] = rec.loan.original_thread
                record['date_created'] = rec.loan.creation_date
                record['date_repayment'] = rec.payment_date
                records.append(record)

            markdown_table = generate_markdown_table(reduce_to_latest_5_loans(records=records))
            
            unpaid_loan_message = ""

            if user_obj.has_unpaid_loan:
                unpaid_loan_message = "\n\n**WARNING: /u/{} has an unpaid loan!**\n\n".format(user_obj.username)

            return Response({'message':
f'''Here are the requested details of the user u/{user_obj.username}. \n\n
{unpaid_loan_message}
**u/{user_obj.username} as a borrower** \n\n
The user has a total of `{user_obj.borrower_pending_loan_count}` outstanding loan(s), for a pending borrowed balance of `{user_obj.borrower_pending_loan_balance} USD`.\n\n
The user has a total of `{user_obj.borrower_completed_loan_count}` completed loan(s), for a total borrowed balance of `{user_obj.borrower_completed_loan_balance} USD`.\n\n
The user has repaid a total of `{user_obj.borrower_repayment_total} USD`.\n\n
\n\n
**u/{user_obj.username} as a lender** \n\n
The user has a total of `{user_obj.lender_pending_loan_count}` outstanding loan(s), for a pending lent out balance of `{user_obj.lender_pending_loan_balance} USD`.\n\n
The user has a total of `{user_obj.lender_completed_loan_count}` completed loan(s), for a total lent out balance of `{user_obj.lender_completed_loan_balance} USD`.\n\n
The user has a total of `{user_obj.lender_unpaid_loan_count}` unpaid loan(s), for a total unpaid balance of `{user_obj.lender_unpaid_loan_balance} USD`.\n\n
\n\n
Here are the details of the last 5 loans for the user: \n\n
{markdown_table}
'''}, status=status.HTTP_200_OK)
        
        except RedditUser.DoesNotExist:
            return Response({'message': f'''User not found!'''}, status=status.HTTP_400_BAD_REQUEST)



class CancelLoanByThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            author = self.request.data['author']
            loan_obj = Loan.objects.filter(thread_id=self.request.data['thread_id'], lender__username=author, is_cancelled=False, is_paid=False)
            if loan_obj.count() > 1:
                return Response({'message': f'''Multiple loans found on this thread! Please use `$cancel_with_id` command instead.'''}, status=status.HTTP_200_OK)
            elif loan_obj.count() == 0:
                raise Loan.DoesNotExist
            
            loan_obj = loan_obj[0]
            loan_obj.is_cancelled = True
            loan_obj.save()

            lender_obj = loan_obj.lender
            borrower_obj = loan_obj.borrower

            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance -= loan_obj.amount_in_usd
            borrower_obj.borrower_pending_loan_count -= 1
            borrower_obj.save()

            return Response({'message': 
                             f'''I have noted that down! \n\n u/{loan_obj.borrower.username} has cancelled their loan of {loan_obj.amount} {loan_obj.currency} from 
u/{loan_obj.lender.username} and the loan is thus marked as cancelled. (Loan ID `{loan_obj.loan_id}`: `Cancelled`) \n\n
**Note**: No further actions will work on this loan (this loan cannot be marked as paid/unpaid/confirmed). If this loan is reinstated, please use the `$loan` command again.
'''}, status=status.HTTP_200_OK)

        except Loan.DoesNotExist:
            return Response({'message': f'''No active loan found! \n\n Please ensure that the lender has used the `$loan` command and the comment has been responded
                              to by the bot. \n\n Paid loans cannot be cancelled. Please contact a mod!'''}, status=status.HTTP_200_OK)


class CancelLoanWithIDView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Check if comment has been replied to
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            loan_obj = Loan.objects.get(loan_id=self.request.data['loan_id'], is_cancelled=False, is_paid=False)
            author = self.request.data['author']
            author_obj, _ = RedditUser.objects.get_or_create(username=author)
            if loan_obj.lender.username != author_obj.username and not author_obj.is_mod:
                return Response({'message': f'''You are not the lender of this loan. You cannot 'cancel' this loan. If this is an error, please contact 
                                a moderator.'''}, status=status.HTTP_200_OK) 
            if loan_obj.is_cancelled:
                return Response({'message': f'''This loan has already been cancelled!'''}, status=status.HTTP_400_BAD_REQUEST)
            
            loan_obj.is_cancelled = True
            loan_obj.save()

            lender_obj = loan_obj.lender
            borrower_obj = loan_obj.borrower

            # Update RedditUser objects
            lender_obj.lender_pending_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count -= 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance -= loan_obj.amount_in_usd
            borrower_obj.borrower_pending_loan_count -= 1
            borrower_obj.save()
            
            if loan_obj.lender.username == author_obj.username:
                return Response({'message': 
f'''I have noted that down! \n\n u/{loan_obj.lender.username} has cancelled their loan of {loan_obj.amount} {loan_obj.currency} with 
u/{loan_obj.borrower.username} and the loan is thus marked as cancelled. (Loan ID `{loan_obj.loan_id}`: `Cancelled`) \n\n
**Note**: No further actions will work on this loan (this loan cannot be marked as paid/unpaid/confirmed). If this loan is reinstated, please use the `$loan` command again.
'''}, status=status.HTTP_200_OK)
            elif author_obj.is_mod:
                return Response({'message':
f'''**Moderator Command** \n\n I have noted that down! \n\n The moderator u/{author_obj.username} has cancelled the loan between the lender u/{loan_obj.lender.username} and the borrower
u/{loan_obj.borrower.username} for the amount of {loan_obj.amount} {loan_obj.currency} and the loan is thus marked as cancelled. (Loan ID `{loan_obj.loan_id}`: `Cancelled`) \n\n
**Note**: No further actions will work on this loan (this loan cannot be marked as paid/unpaid/confirmed). If this loan is reinstated, please use the `$loan` command again.
'''}, status=status.HTTP_200_OK)
        except Loan.DoesNotExist:
            return Response({'message': f'''No existing loan found! Please ensure that the lender has used the `$loan` command and the comment has been responded
                              to by the bot. \n\n Paid loans cannot be cancelled. Please contact a mod!'''}, status=status.HTTP_200_OK)



class CancelPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if check_if_comment_has_been_replied_to(self.request.data['comment_id']):
            return Response({'message': f'''This comment has already been replied to!'''}, status=status.HTTP_400_BAD_REQUEST)
        else:
            CommentsRepliedTo.objects.create(comment_reddit_id=self.request.data['comment_id'])

        try:
            payment_id = request.data.get('payment_id')
            author = request.data.get('author')

            if not payment_id:
                return Response({'message': 'Please provide a valid payment ID.'}, status=status.HTTP_400_BAD_REQUEST)

            author_obj, _ = RedditUser.objects.get_or_create(username=author)
            payment = Payment.objects.get(id=payment_id, is_cancelled=False)
            loan_obj = payment.loan

            # Ensure only the lender or a mod can cancel
            if loan_obj.lender.username != author_obj.username and not author_obj.is_mod:
                return Response({'message': 'Only the lender or a moderator can cancel this payment.'}, status=status.HTTP_403_FORBIDDEN)

            # Prevent double cancellation
            if payment.is_cancelled:
                return Response({'message': 'This payment has already been canceled.'}, status=status.HTTP_400_BAD_REQUEST)

            loan_obj.is_paid = False
            loan_obj.save()
            
            # Reverse the payment effects
            lender_obj = loan_obj.lender
            borrower_obj = loan_obj.borrower

            lender_obj.lender_pending_loan_balance += loan_obj.amount_in_usd
            lender_obj.lender_pending_loan_count += 1
            lender_obj.lender_completed_loan_balance -= loan_obj.amount_in_usd
            lender_obj.lender_completed_loan_count -= 1
            lender_obj.save()

            borrower_obj.borrower_pending_loan_balance += loan_obj.amount_in_usd
            borrower_obj.borrower_pending_loan_count += 1
            borrower_obj.borrower_completed_loan_balance -= loan_obj.amount_in_usd
            borrower_obj.borrower_completed_loan_count -= 1
            borrower_obj.borrower_repayment_total -= loan_obj.amount_in_usd
            borrower_obj.save()

            # Mark payment as canceled
            payment.is_cancelled = True
            payment.save()

            return Response({'message': f'Payment ID `{payment_id}` has been successfully canceled.'}, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            return Response({'message': 'No active payment found with this ID.'}, status=status.HTTP_400_BAD_REQUEST)






class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]