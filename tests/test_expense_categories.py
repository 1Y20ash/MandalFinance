import pytest

from app.extensions import db
from app.models.expense import Expense, ExpenseCategory
from app.models.audit import AuditLog
from app.services.expense_category_service import ExpenseCategoryService
from app.models.auth import User


def test_admin_can_create_category(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        category = ExpenseCategoryService.create('Sound & Lighting', 'Stage and sound equipment', admin)
        assert category.name == 'Sound & Lighting'
        assert category.is_active is True
        assert AuditLog.query.filter_by(entity_type='EXPENSE_CATEGORY', entity_id=category.id, action='CREATE').count() == 1


def test_duplicate_category_name_is_case_insensitive(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        with pytest.raises(ValueError, match='already exists'):
            ExpenseCategoryService.create('decoration', '', admin)


def test_category_update_and_deactivation_preserve_historical_expenses(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        category = ExpenseCategory.query.filter_by(name='Decoration').first()
        ExpenseCategoryService.update(category.id, 'Festival Decoration', 'Decorations and materials', admin)
        ExpenseCategoryService.set_active(category.id, False, admin)
        db.session.refresh(category)
        assert category.name == 'Festival Decoration'
        assert category.is_active is False
        assert category.expenses == []


def test_category_cannot_be_used_for_new_expenses_when_inactive(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        category = ExpenseCategory.query.filter_by(name='Decoration').first()
        ExpenseCategoryService.set_active(category.id, False, admin)
        with pytest.raises(ValueError, match='not active'):
            from datetime import date
            from app.services.expense_service import ExpenseService
            ExpenseService.submit_expense(
                event_id=1, category_id=category.id, title='Flowers', description='Festival flowers',
                amount='100.00', expense_date=date(2026, 9, 1), created_by_user=admin,
            )


def test_non_admin_cannot_manage_categories(app):
    with app.app_context():
        user = User.query.filter_by(username='volunteer').first()
        with pytest.raises(PermissionError):
            ExpenseCategoryService.create('Restricted', '', user)
