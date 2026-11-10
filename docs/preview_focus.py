"""Render focus-chart/streak screenshots with fictional temporary data."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase,QFont
from PySide6.QtTest import QTest
from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.productivity.focus_session import FocusSessionManager
from app.ui.dashboard import Dashboard


def main():
    app=QApplication([])
    app.setStyle('Fusion')
    for name in ('segoeui.ttf','segoeuib.ttf','seguisb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    app.setFont(QFont('Segoe UI',10))
    output=Path(__file__).parent/'images'
    with tempfile.TemporaryDirectory() as temp:
        settings=SettingsManager(Path(temp)/'config.json')
        settings.set('animations_enabled',False)
        settings.set('tracking_mode','manual')
        settings.set('demo_mode',True)
        db=DatabaseManager(Path(temp)/'preview.db')
        for offset,minutes in ((0,10),(2,375),(3,120),(5,60),(7,30),(12,15)):
            db.record_focus_session(minutes*60,end_time=datetime.now()-timedelta(days=offset),completed=offset!=0,note='Fictional chart fixture')
        db.repair_streak_day(datetime.now().date()-timedelta(days=1))
        dashboard=Dashboard(db,settings,FocusSessionManager())
        dashboard.show()
        for _ in range(200):
            if dashboard.evolution_controller.snapshot is not None:
                break
            QTest.qWait(10)
        page=dashboard.pages.currentWidget()
        app.processEvents()
        dashboard.grab().save(str(output/'focus-dashboard.png'))
        page.widget().grab().save(str(output/'focus-overview-full.png'))
        dashboard.activity_chart.grab().save(str(output/'focus-chart.png'))
        dashboard.heatmap.grab().save(str(output/'focus-calendar.png'))
        dashboard.resize(960,640)
        app.processEvents()
        if page.horizontalScrollBar().maximum()!=0:
            raise RuntimeError('Overview overflows at minimum width')
        page.ensureWidgetVisible(dashboard.repair_button)
        app.processEvents()
        dashboard.grab().save(str(output/'streak-care-small.png'))
        dashboard.measure_picker.setCurrentIndex(1)
        dashboard.activity_chart.grab().save(str(output/'focus-empty-tracked.png'))
        dashboard.evolution_controller.close()
        dashboard.close()
    print('Focus previews saved in docs/images; temporary fixture data only.')


if __name__=='__main__':
    main()
