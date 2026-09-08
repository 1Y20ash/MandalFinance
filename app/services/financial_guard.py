from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session
from app.extensions import db

FINANCIAL_EVENT_MODELS = {'Donation', 'Sponsorship', 'MemberContribution', 'Expense', 'Transaction', 'BudgetCategory', 'Budget', 'ContributionReceipt'}


def _assert_open(session, obj):
    event_id = getattr(obj, 'event_id', None)
    if not event_id: return
    from app.models.mandal import Event
    event = session.get(Event, event_id)
    if not event: return
    if event.status != 'OPEN' or (event.financial_year and event.financial_year.is_locked):
        if obj.__class__.__name__ == 'Transaction' and getattr(obj, 'transaction_type', None) == 'REVERSAL': return
        raise ValueError(f'Financial event {event.title} is locked; new or modified financial records are forbidden.')


def install_financial_guard():
    if getattr(db, '_mandal_financial_guard_installed', False): return
    @sqlalchemy_event.listens_for(Session, 'before_flush')
    def _guard(session, flush_context, instances):
        for obj in list(session.new):
            if obj.__class__.__name__ in FINANCIAL_EVENT_MODELS: _assert_open(session, obj)
        for obj in list(session.dirty):
            if obj.__class__.__name__ not in FINANCIAL_EVENT_MODELS: continue
            if obj.__class__.__name__ == 'Transaction' and getattr(obj, 'is_reversed', False): continue
            _assert_open(session, obj)
    db._mandal_financial_guard_installed = True
