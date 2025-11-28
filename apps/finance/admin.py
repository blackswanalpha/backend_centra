from django.contrib import admin
from .models import (
    Invoice, InvoiceItem, Payment, Expense, Budget, BudgetItem,
    Payroll, PayrollEarning, PayrollDeduction
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['description', 'quantity', 'unit_price', 'tax_rate', 'total_price']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client', 'issue_date', 'due_date', 'total_amount', 'status']
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'client__company_name']
    inlines = [InvoiceItemInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_reference', 'client', 'amount', 'payment_method', 'payment_date', 'status']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['payment_reference', 'client__company_name', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'category', 'amount', 'expense_date', 'status', 'submitted_by']
    list_filter = ['status', 'category', 'expense_date']
    search_fields = ['expense_number', 'description', 'vendor_name']
    readonly_fields = ['created_at', 'updated_at']


class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 1
    fields = ['category', 'allocated_amount', 'spent_amount', 'remaining_amount']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'budget_type', 'total_budget', 'start_date', 'end_date', 'is_active']
    list_filter = ['budget_type', 'is_active', 'start_date']
    search_fields = ['name', 'description']
    inlines = [BudgetItemInline]
    readonly_fields = ['created_at', 'updated_at']


class PayrollEarningInline(admin.TabularInline):
    model = PayrollEarning
    extra = 1
    fields = ['earning_type', 'description', 'amount']


class PayrollDeductionInline(admin.TabularInline):
    model = PayrollDeduction
    extra = 1
    fields = ['deduction_type', 'description', 'amount']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'pay_period', 'start_date', 'end_date', 'net_pay', 'status', 'payment_date']
    list_filter = ['status', 'pay_period', 'payment_method', 'start_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id', 'payment_reference']
    inlines = [PayrollEarningInline, PayrollDeductionInline]
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee',)
        }),
        ('Pay Period', {
            'fields': ('pay_period', 'start_date', 'end_date')
        }),
        ('Salary Components', {
            'fields': ('base_salary', 'gross_pay', 'total_deductions', 'net_pay', 'currency')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_date')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_date', 'processed_date', 'payment_reference')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayrollEarning)
class PayrollEarningAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'earning_type', 'description', 'amount', 'created_at']
    list_filter = ['earning_type', 'created_at']
    search_fields = ['description', 'payroll__employee__first_name', 'payroll__employee__last_name']


@admin.register(PayrollDeduction)
class PayrollDeductionAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'deduction_type', 'description', 'amount', 'created_at']
    list_filter = ['deduction_type', 'created_at']
    search_fields = ['description', 'payroll__employee__first_name', 'payroll__employee__last_name']

