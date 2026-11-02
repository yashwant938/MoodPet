"""Fictional fixtures, only invoked inside --demo's disposable profile."""
from datetime import datetime, timedelta


def populate_demo(db, settings):
    settings.set('onboarding_complete', True)
    settings.set('tracking_mode', 'manual')
    settings.set('personality', 'gentle')
    settings.set('demo_mode', True)
    task = db.create_task('Explore a small idea', 'Demo project', 1500)
    for i in range(36):
        db.record_focus_session(1500, end_time=datetime.now()-timedelta(days=i//3,hours=i%3),
                                note='Fictional demo session', task_id=task)
    db.update_task(task,status='completed')
    # Historic fixture unlocks should not replay when the preview opens.
    db.get_evolution_snapshot(claim_unlocks=True)
