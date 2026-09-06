from app.extensions import db
from app.models.expense import Expense, ExpenseCategory
from app.services.audit_service import AuditService


class ExpenseCategoryService:
    """Business rules for maintaining expense categories without damaging history."""

    @staticmethod
    def _validate_name(name):
        name = (name or '').strip()
        if len(name) < 2:
            raise ValueError('Category name must contain at least 2 characters.')
        if len(name) > 100:
            raise ValueError('Category name cannot exceed 100 characters.')
        return name

    @staticmethod
    def _validate_description(description):
        description = (description or '').strip()
        if len(description) > 255:
            raise ValueError('Category description cannot exceed 255 characters.')
        return description or None

    @staticmethod
    def create(name, description, actor):
        if not actor or not getattr(actor, 'is_admin', False):
            raise PermissionError('Only administrators can manage expense categories.')
        name = ExpenseCategoryService._validate_name(name)
        description = ExpenseCategoryService._validate_description(description)
        if ExpenseCategory.query.filter(db.func.lower(ExpenseCategory.name) == name.lower()).first():
            raise ValueError(f'Expense category "{name}" already exists.')
        category = ExpenseCategory(name=name, description=description, is_active=True)
        try:
            db.session.add(category)
            db.session.flush()
            AuditService.log_action(
                action='CREATE', entity_type='EXPENSE_CATEGORY', entity_id=category.id,
                description=f'Created expense category "{category.name}"', commit=False,
            )
            db.session.commit()
            return category
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update(category_id, name, description, actor):
        if not actor or not getattr(actor, 'is_admin', False):
            raise PermissionError('Only administrators can manage expense categories.')
        category = db.session.get(ExpenseCategory, category_id)
        if not category:
            raise ValueError('Expense category not found.')
        name = ExpenseCategoryService._validate_name(name)
        description = ExpenseCategoryService._validate_description(description)
        duplicate = ExpenseCategory.query.filter(
            db.func.lower(ExpenseCategory.name) == name.lower(),
            ExpenseCategory.id != category.id,
        ).first()
        if duplicate:
            raise ValueError(f'Expense category "{name}" already exists.')
        old_name = category.name
        try:
            category.name = name
            category.description = description
            AuditService.log_action(
                action='UPDATE', entity_type='EXPENSE_CATEGORY', entity_id=category.id,
                description=f'Updated expense category "{old_name}" to "{category.name}"', commit=False,
            )
            db.session.commit()
            return category
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def set_active(category_id, is_active, actor):
        if not actor or not getattr(actor, 'is_admin', False):
            raise PermissionError('Only administrators can manage expense categories.')
        category = db.session.get(ExpenseCategory, category_id)
        if not category:
            raise ValueError('Expense category not found.')
        if not is_active and Expense.query.filter_by(category_id=category.id).first():
            # Historical expenses keep their category; deactivation only removes it from new submissions.
            pass
        try:
            category.is_active = bool(is_active)
            action = 'ACTIVATE' if category.is_active else 'DEACTIVATE'
            AuditService.log_action(
                action=action, entity_type='EXPENSE_CATEGORY', entity_id=category.id,
                description=f'{action.title()}d expense category "{category.name}"', commit=False,
            )
            db.session.commit()
            return category
        except Exception:
            db.session.rollback()
            raise
