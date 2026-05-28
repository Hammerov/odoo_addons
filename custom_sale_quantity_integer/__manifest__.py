{
    'name': 'Custom Sale Quantity Integer',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Make quantity field accept only whole numbers',
    'depends': ['sale', 'sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'author': 'Hammerov',
}