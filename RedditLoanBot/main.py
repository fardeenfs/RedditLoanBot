import re
from time import sleep
import praw
import os
from dotenv import load_dotenv
import requests

load_dotenv()

def get_token():
    # Replace '/api-token-auth/' with the correct endpoint for your API
    response = requests.post(f"{os.getenv('BACKEND_URL')}/api/token/", data={
        'username': os.getenv('BACKEND_USERNAME'),
        'password': os.getenv('BACKEND_PASSWORD')
    })
    response.raise_for_status()  # This will raise an exception for HTTP errors
    return response.json()['access']  # Adjust the key according to your API response


def main():

    reddit = praw.Reddit(
        client_id= os.getenv('CLIENT_ID'), #Your Personal Use Script
        client_secret=os.getenv('CLIENT_SECRET'), #Your Secret key
        password=os.getenv('PASSWORD'), #Your Reddit Account Password
        user_agent=os.getenv('USER_AGENT'), #user agent name
        username=os.getenv('REDDITUSERNAME'), #Your Reddit Username
    )

    subreddit = reddit.subreddit(os.getenv('SUBREDDIT'))
    comment_stream = subreddit.stream.comments(skip_existing=True)
   
    for comment in comment_stream:
        
        print(comment.body.split()[0])
        print(len(comment.body), comment.id)
        # check if the first word is $loan
        if comment.body.split()[0].lower() == '$loan':
            request_loan(comment)

        # check if the first word is $confirm_with_id
        if comment.body.split()[0].lower() in ['$confirm\_with\_id', '$confirm_with_id']:
            confirm_loan_with_id(comment)

        # check if the first word is $paid
        if comment.body.split()[0].lower() in ['$paid\_with\_id', '$paid_with_id']:
            paid_loan_with_id(comment)

        # check if the first word is $paid
        if comment.body.split()[0].lower() == '$paid':
            paid_loan_by_thread(comment)

        # check if the first word is $confirm
        if comment.body.split()[0].lower() in ['$confirm', '$confirmed']:
            confirm_loan_by_thread(comment)

        # check if the first word is $unpaid
        if comment.body.split()[0].lower() == '$unpaid':
            unpaid_loan_by_thread(comment, subreddit)

        # check if the first word is $unpaid_with_id
        if comment.body.split()[0].lower() in ['$unpaid\_with\_id', '$unpaid_with_id']:
            unpaid_loan_with_id(comment, subreddit)

        # check if the first word is $check
        if comment.body.split()[0].lower() == '$check':
            check_user(comment)

        # check if the first word is $cancel
        if comment.body.split()[0].lower() == '$cancel':
            cancel_loan_by_thread(comment)

        # check if the first word is $cancel_with_id
        if comment.body.split()[0].lower() in ['$cancel\_with\_id', '$cancel_with_id']:
            cancel_loan_with_id(comment)


def request_loan(comment):
    lender = comment.author
    submission = comment.submission
    borrower = submission.author
    print("Loan", comment, lender, borrower, submission.url, comment.created_utc, comment.body)

    comment_body = comment.body.split()
    if len(comment_body) >= 2:
        if comment_body[1].startswith('u/'):
            borrower = comment_body[1][2:]
            amount = str(comment_body[2]) if len(comment_body) >= 3 else None
            currency = str(comment_body[3]) if len(comment_body) >= 4 else 'USD'
        elif comment_body[1].startswith('/u/'):
            borrower = comment_body[1][3:]
            amount = str(comment_body[2]) if len(comment_body) >= 3 else None
            currency = str(comment_body[3]) if len(comment_body) >= 4 else 'USD'
        else:
            amount = str(comment_body[1])
            currency = str(comment_body[2]) if len(comment_body) >= 3 else 'USD'
    else:
        data = {
                comment.id: comment.body,
            }
        response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/track-comment/", data, comment)
        
        if response != 400:
            comment.reply("I couldn't understand that! Please specify the amount and currency. \n\n Example: $loan 100 USD")
        return()
    
    
    red_amount = re.sub("[^0-9.]", "", amount)
    
    if len(red_amount) - len(amount) > 1 or not red_amount:
        data = {
                comment.id: comment.body,
            }
        response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/track-comment/", data, comment)
        
        if response != 400:
            comment.reply("I couldn't understand that! Please specify the amount and currency. \n\n Example: $loan 100 USD")
        return()

    data = {
        'lender': lender,
        'borrower': borrower,
        'amount': red_amount,
        'currency': currency,
        'original_thread': submission.url,
        'thread_id': submission.id,
        'comment_id': comment.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/loans/", data, comment)

    

def confirm_loan_with_id(comment):
    author = comment.author
    comment_body = comment.body.split()

    if len(comment_body) >= 2:
        loan_id = str(comment_body[1])
    else:
        return()

    data = {
        'author': author,
        'loan_id': loan_id,
        'comment_id': comment.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/confirm-loan-with-id/", data, comment)


def confirm_loan_by_thread(comment):
    author = comment.author

    data = {
        'author': author,
        'comment_id': comment.id,
        'thread_id': comment.submission.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/confirm-loan-by-thread/", data, comment)


def paid_loan_with_id(comment):  
    author = comment.author
    comment_body = comment.body.split()

    amount = ''
    currency = ''

    if len(comment_body) >= 4:
        loan_id = str(comment_body[1])
        amount = str(comment_body[2])
        currency = str(comment_body[3])
    elif len(comment_body) == 3:
        loan_id = str(comment_body[1])
        amount = str(comment_body[2])
        currency = 'USD'
    elif len(comment_body) == 2:
        loan_id = str(comment_body[1])
        amount = ''
        currency = ''
    else:
        return()
        
    
    red_amount = re.sub("[^0-9.]", "", amount)
    
    if len(red_amount) - len(amount) > 1:
        data = {
                comment.id: comment.body,
            }
        response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/track-comment/", data, comment)
        
        if response != 400:
            comment.reply("I couldn't understand that! Please use this format. \n\n `$paid_with_id [Loan ID] [Amount] [Currency]`")
        return()

    data = {
        'author': author,
        'loan_id': loan_id,
        'amount': red_amount,
        'currency': currency,
        'comment_id': comment.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/pay-loan-with-id/", data, comment)


def paid_loan_by_thread(comment):
    author = comment.author
    comment_body = comment.body.split()

    amount = ''
    currency = ''

    if len(comment_body) >= 3:
        amount = str(comment_body[1])
        currency = str(comment_body[2])
    elif len(comment_body) == 2:
        amount = str(comment_body[1])
        currency = 'USD'

    red_amount = re.sub("[^0-9.]", "", amount)
    
    if len(red_amount) - len(amount) > 1:
        data = {
                comment.id: comment.body,
            }
        response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/track-comment/", data, comment)
        
        if response != 400:
            comment.reply("I couldn't understand that! Please use this format. \n\n `$paid_with_id [Loan ID] [Amount] [Currency]`  \n\n Example: `$paid 2 100 USD`")
        return()

    data = {
        'author': author,
        'amount': red_amount,
        'currency': currency,
        'comment_id': comment.id,
        'thread_id': comment.submission.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/pay-loan-by-thread/", data, comment)


def unpaid_loan_with_id(comment, subreddit):
    author = comment.author
    comment_body = comment.body.split()

    if len(comment_body) >= 2:
        loan_id = str(comment_body[1])
    else:
        return()

    data = {
        'author': author,
        'loan_id': loan_id,
        'comment_id': comment.id,
    }

    response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/unpaid-loan-with-id/", data, comment)
    if response != 400:
        send_mod_mail(subreddit,'Unpaid Loan Alert', f"u/{comment.author} has reported an unpaid loan on this thread: {comment.submission.url}. \n\n This is the link to the comment: {comment.permalink}")



def unpaid_loan_by_thread(comment, subreddit):
    author = comment.author

    data = {
        'author': author,
        'thread_id': comment.submission.id,
        'comment_id': comment.id,
    }

    response = send_to_backend(f"{os.getenv('BACKEND_URL')}/api/unpaid-loan-by-thread/", data, comment)
    if response != 400:
        send_mod_mail(subreddit,'Unpaid Loan Alert', f"u/{comment.author} has reported an unpaid loan on this thread: {comment.submission.url}. \n\n This is the link to the comment: {comment.permalink}")


def check_user(comment):
    comment_body = comment.body.split()

    if len(comment_body) >= 2:
        username = comment_body[1]
    else:
        username = str(comment.author)

    if username.startswith('u/'):
        username = username[2:]
    elif username.startswith('/u/'):
        username = username[3:]

    data = {
        'username': username,
        'comment_id': comment.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/check-user-loans/", data, comment)


def cancel_loan_by_thread(comment):
    author = comment.author

    data = {
        'author': author,
        'comment_id': comment.id,
        'thread_id': comment.submission.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/cancel-loan-by-thread/", data, comment)


def cancel_loan_with_id(comment):
    
    author = comment.author
    comment_body = comment.body.split()

    if len(comment_body) >= 2:
        loan_id = comment_body[1]
    else:
        return()

    data = {
        'author': author,
        'loan_id': loan_id,
        'comment_id': comment.id,
    }

    send_to_backend(f"{os.getenv('BACKEND_URL')}/api/cancel-loan-with-id/", data, comment)




def send_to_backend(url, data, comment):
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(url, data=data, headers=headers)
    print(response.json())
    if response.status_code in [200, 201]:
        reply_message = response.json()['message']
        try:
            comment.reply(reply_message)
            print(f"Replied with: {reply_message}")
        except Exception as e:
            print(f"Error in replying: {e}")


    if response.status_code == 401:  # or whatever code your API returns for expired/invalid token
        # Token might have expired, fetch a new one
        token = get_token()
        headers = {'Authorization': f'Token {token}'}
        
        # Retry the request with the new token
        response = requests.post(
            url, 
            data=data, 
            headers=headers
        )
        print(response.json())
        if response.status_code in [200, 201]:
            reply_message = response.json()['message']
            try:
                comment.reply(reply_message)
                print(f"Replied with: {reply_message}")
            except Exception as e:
                print(f"Error in replying: {e}")
    
    return response.status_code


def send_mod_mail(subreddit, subject, message):
    subreddit.message(subject=subject, message=message)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sleep(60)
        main()