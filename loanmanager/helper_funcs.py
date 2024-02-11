import decimal

import requests


def reduce_to_latest_5_loans(records):
    # Combine all records
    all_records = []
    for record in records:
        all_records.append({
            'loan_id': str(record["loan_id"]),
            'lender': record["lender"],
            'borrower': record["borrower"],
            'amount': str(record["amount"]) + ' ' + record["currency"],
            'repaid': str(record["repaid"])  + ' ' + record["repayment_currency"],
            'confirmed': 'Yes' if record["confirmed"] else 'No',
            'paid': 'Yes' if record["paid"] else 'No',
            'unpaid': 'Yes' if record["unpaid"] else 'No',
            'loan_thread': record["loan_thread"] ,
            'date_created': record["date_created"],
            'date_repayment': record["date_repayment"]
        })

    # Sort records by date_created in descending order
    all_records.sort(key=lambda x: x['date_created'], reverse=True)

    # Take the first 5 records
    return all_records[:5]

def generate_markdown_table(loans):
    # Headers
    headers = ["Loan ID", "Lender", "Borrower", "Amount", "Repayment", "Paid?", "Unpaid?", "Loan Thread", "Date Created", "Date Repayment"]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    # Rows
    rows = []
    for loan in loans:
        row = [
            loan['loan_id'],
            loan['lender'],
            loan['borrower'],
            loan['amount'],
            loan['repaid'],
            loan['paid'],
            loan['unpaid'],
            loan['loan_thread'],
            loan['date_created'].strftime("%Y-%m-%d") if loan['date_created'] else "",
            loan['date_repayment'].strftime("%Y-%m-%d") if loan['date_repayment'] else ""
        ]
        rows.append("| " + " | ".join(row) + " |")

    # Combine all parts
    return "\n".join([header_line, separator_line] + rows)


def convert_currency(amount, currency_to_convert_to):
    # Replace {currency_to_convert_to} with the actual currency code
    url = f"https://raw.githubusercontent.com/fawazahmed0/currency-api/1/latest/currencies/usd/{currency_to_convert_to.lower()}.min.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        
        # Parse the JSON response
        data = response.json()
        print('API response:', data)
        exchange_rate = decimal.Decimal(str(data[currency_to_convert_to.lower()]))

        # Convert the amount
        converted_amount = amount / exchange_rate

        return converted_amount.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
    except requests.RequestException as e:
        # Handle any errors that occur during the request
        print(f"An error occurred: {e}")
        return None
