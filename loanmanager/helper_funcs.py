import decimal

import requests
from .models import CurrencyConversion

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
    try:
        # Convert the amount
        conversion = CurrencyConversion.objects.filter(currency=currency_to_convert_to.upper()).first()
        if not conversion:
            raise ValueError(f"Conversion rate for {currency_to_convert_to} not found")
        converted_amount = amount * conversion.conversion_rate_to_usd

        return converted_amount.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
    except Exception as e:
        # Handle any errors that occur during the request
        print(f"An error occurred: {e}")
        return None
