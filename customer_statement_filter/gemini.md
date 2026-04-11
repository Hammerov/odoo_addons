Here is the updated and expanded gemini.md. customer_statement_filter Module
1. Project Goal
Create a standalone Odoo 19 module that provides a "Wizard" interface for generating customer statements, replicating the QuickBooks desktop filter experience. This replaces the existing Studio model x_statement_wizard.

2. Module Directory Structure
Plaintext
customer_statement_filter/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── statement_wizard.py
├── views/
│   └── statement_wizard_views.xml
└── security/
    └── ir.model.access.csv
3. Implementation Details
A. The Manifest (__manifest__.py)
Defines the module metadata.

Dependencies: account, account_followup (Odoo Enterprise functionality for statements).

Data: Views and Security files.

B. The Model Logic (models/statement_wizard.py)
This file defines the TransientModel (a temporary data model that doesn't bloat your database).

Key Fields:

date_from/date_to: Limits the transaction scope.

partner_ids: A many2many selection field allowing users to pick specific customers.

exclude_zero_balance: A logic toggle to skip customers who don't owe money.

The Action: A Python function action_print_statements that filters the res.partner records and passes them to the Odoo report engine.

C. The Interface (views/statement_wizard_views.xml)
This file contains the XML for the Form view.

Layout: Uses <group> tags to create two columns (Period and Options).

Notebook: Adds a searchable list of customers at the bottom.

Menu: Injects the "Customer Statements" link under Accounting > Customers.

D. Security (security/ir.model.access.csv)
Standard Odoo permissions to allow the Accounting group to use this wizard.

4. Migration Plan (Studio to Custom)
Backup: Keep your studio_customization.zip as a reference.

Clean Up: Once the custom module is installed, we will delete the Studio version of x_statement_wizard to avoid duplicate menu items.

Naming Convention: We move from x_statement_wizard (Studio name) to customer.statement.wizard (Professional name).

5. Visual Workflow
User opens Menu -> Form Popup appears.

User selects Dates/Customers -> Input stored in Transient Model.

User clicks "Print PDF" -> Server Action processes logic.

Odoo generates Report -> PDF downloads automatically.
Gemini Project Update: Customer Statement Filter
1. Project Status
Core Goal: Create a QuickBooks-style Customer Statement wizard with running balances.

Working: Wizard UI, Menu item, Module installation, PDF Generation (Triggering).

Broken: The PDF output is currently blank (White page/No data).

2. Current Technical Blockers
Data Linkage: The AbstractModel in reports/partner_statement_report.py does not seem to be injecting the docs list into the QWeb context.

Naming Sync: We need to verify that report_name in XML matches _name in Python exactly.

Variable Scope: The XML is using doc['lines'], which requires the Python _get_report_values to return a list of dictionaries.
