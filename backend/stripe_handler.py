import stripe
import os
from flask import url_for


stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


def stripe_url_maker(module_title, module_price):
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "aud",
                "product_data": {
                    "name": module_title,
                },
                # ppayment in cents ( Note)
                "unit_amount": int(module_price) * 100,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=url_for("view_order", _external=True),
        cancel_url=url_for("modules", _external=True),
    )
    
    return checkout_session.url









