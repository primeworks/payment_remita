# -*- coding: utf-8 -*-

{
    'name': 'Remita Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Remita Implementation',
    'version': '1.0',
    'description': """Remita Payment Acquirer""",
    'author': 'Silicon Streets',
    'depends': ['payment'],
    'data': [
        'views/remita.xml',
        'views/payment_acquirer.xml',
        'data/remita.xml',
    ],
    'installable': True,
}
