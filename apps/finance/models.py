from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client
from apps.employees.models import Employee


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('VIEWED', 'Viewed'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Invoice Details
    issue_date = models.DateField()
    due_date = models.DateField()
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Payment Details
    payment_terms = models.CharField(max_length=255, default='Net 30')
    payment_method = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-issue_date']
        
    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    
    # Item Details
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Tax
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'invoice_items'
        
    def __str__(self):
        return f"{self.description} - {self.invoice.invoice_number}"


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('MPESA', 'M-Pesa'),
        ('CARD', 'Credit/Debit Card'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Payment Details
    payment_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Dates
    payment_date = models.DateField()
    received_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Bank Details (for bank transfers)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # System Fields
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments_recorded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
        
    def __str__(self):
        return f"{self.payment_reference} - {self.client.name}"


class Expense(models.Model):
    EXPENSE_CATEGORIES = [
        ('OFFICE', 'Office Expenses'),
        ('TRAVEL', 'Travel & Transport'),
        ('TRAINING', 'Training & Development'),
        ('EQUIPMENT', 'Equipment'),
        ('SOFTWARE', 'Software & Subscriptions'),
        ('UTILITIES', 'Utilities'),
        ('MARKETING', 'Marketing & Advertising'),
        ('PROFESSIONAL', 'Professional Services'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]

    # Expense Details
    expense_number = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    description = models.CharField(max_length=255)
    
    # Financial
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Dates
    expense_date = models.DateField()
    
    # Vendor Details
    vendor_name = models.CharField(max_length=255, blank=True)
    vendor_contact = models.CharField(max_length=255, blank=True)
    
    # Status & Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses_submitted')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses_approved')
    approval_date = models.DateField(null=True, blank=True)
    
    # Payment
    paid_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Files
    receipt_file = models.FileField(upload_to='receipts/', blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']
        
    def __str__(self):
        return f"{self.expense_number} - {self.description}"


class Budget(models.Model):
    BUDGET_TYPES = [
        ('ANNUAL', 'Annual Budget'),
        ('QUARTERLY', 'Quarterly Budget'),
        ('PROJECT', 'Project Budget'),
        ('DEPARTMENT', 'Department Budget'),
    ]

    name = models.CharField(max_length=255)
    budget_type = models.CharField(max_length=20, choices=BUDGET_TYPES)
    description = models.TextField(blank=True)
    
    # Financial
    total_budget = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    
    # Period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Assignment
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='budgets_owned')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='budgets_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'budgets'
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.name} - {self.budget_type}"


class BudgetItem(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=20, choices=Expense.EXPENSE_CATEGORIES)
    
    # Budget Allocation
    allocated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'budget_items'
        unique_together = ['budget', 'category']

    def __str__(self):
        return f"{self.budget.name} - {self.get_category_display()}"


class Payroll(models.Model):
    """
    Payroll model to track employee payroll records.
    """
    PAY_PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BI_WEEKLY', 'Bi-Weekly'),
        ('MONTHLY', 'Monthly'),
        ('DYNAMIC', 'Dynamic'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('MPESA', 'M-Pesa'),
        ('OTHER', 'Other'),
    ]

    # Employee Reference
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_records')

    # Pay Period
    pay_period = models.CharField(max_length=20, choices=PAY_PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()

    # Salary Components
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2)

    # Currency
    currency = models.CharField(max_length=3, default='KES')

    # Status & Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payrolls_approved')
    approved_date = models.DateTimeField(null=True, blank=True)

    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='BANK_TRANSFER')
    payment_date = models.DateField(null=True, blank=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payrolls_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
        ]

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} - {self.start_date} to {self.end_date}"


class PayrollEarning(models.Model):
    """
    Additional earnings for a payroll record (bonuses, commissions, etc.)
    """
    EARNING_TYPE_CHOICES = [
        ('BONUS', 'Bonus'),
        ('COMMISSION', 'Commission'),
        ('OVERTIME', 'Overtime'),
        ('ALLOWANCE', 'Allowance'),
        ('REIMBURSEMENT', 'Reimbursement'),
        ('OTHER', 'Other'),
    ]

    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='earnings')
    earning_type = models.CharField(max_length=20, choices=EARNING_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_earnings'
        ordering = ['earning_type']

    def __str__(self):
        return f"{self.get_earning_type_display()} - {self.amount}"


class PayrollDeduction(models.Model):
    """
    Deductions from a payroll record (taxes, insurance, etc.)
    """
    DEDUCTION_TYPE_CHOICES = [
        ('TAX', 'Tax'),
        ('INSURANCE', 'Insurance'),
        ('PENSION', 'Pension/Retirement'),
        ('LOAN', 'Loan Repayment'),
        ('ADVANCE', 'Salary Advance'),
        ('OTHER', 'Other'),
    ]

    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_deductions'
        ordering = ['deduction_type']

    def __str__(self):
        return f"{self.get_deduction_type_display()} - {self.amount}"