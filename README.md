# Rental Income Manager

A comprehensive Django application for managing rental properties, tenants, income, and expenses.

## Features

- **Property Management**: Add, edit, and track details of all your rental properties
- **Tenant Management**: Store tenant information, contact details, and lease agreements
- **Income Tracking**: Record and categorize all rental payments
- **Expense Management**: Track property-related expenses and maintenance costs
- **Financial Reports**: Generate income and expense reports by property, month, or year
- **Dashboard**: Visual overview of your rental business performance
- **Data Export**: Export reports to CSV or PDF formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rental-income-manager.git
cd rental-income-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Access the admin at http://127.0.0.1:8000/admin/ and the application at http://127.0.0.1:8000/

## Technology Stack

- **Backend**: Python 3.9+ / Django 4.2+
- **Frontend**: Bootstrap 5, JavaScript, Chart.js
- **Database**: SQLite (development) / PostgreSQL (production recommended)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request.
