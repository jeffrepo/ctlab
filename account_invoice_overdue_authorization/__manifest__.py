{
    "name": "Customer Invoice Overdue Authorization",
    "summary": "Require authorization before posting customer invoices when the customer has overdue unpaid invoices.",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "CTLab",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/account_invoice_overdue_authorization_security.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
