def build_pay_by_square(iban: str, amount: float, variable_symbol: str, beneficiary_name: str,
                         note: str = "", bic: str = "", currency: str = "EUR",
                         due_date=None) -> str:
    from decimal import Decimal
    from by_square import PayQR, Payment, PaymentOption, BankAccount

    payment = Payment(
        payment_options=PaymentOption.PAYMENT_ORDER,
        amount=Decimal(str(amount)),
        currency_code=currency,
        bank_accounts=[BankAccount(iban=iban, bic=bic)],
        variable_symbol=variable_symbol,
        payment_due_date=due_date,
        payment_note=note,
        beneficiary_name=beneficiary_name,
    )

    return PayQR(payments=[payment]).encode()