"""Reproduce screenshots with a temporary, fictional profile; never load user data."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFontDatabase, QFont, QImage, QPainter, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.productivity.progression import RULES, STAGES, progress_for
from app.productivity.rewards import RewardService
from app.productivity.focus_session import FocusSessionManager
from app.ui.dashboard import Dashboard
from app.ui.character import HumanCharacterWidget
from app.character.emotions import EmotionalPose
from app.demo import populate_demo


def main():
    app=QApplication([])
    app.setStyle('Fusion')
    for name in ('segoeui.ttf','segoeuib.ttf','seguisb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    app.setFont(QFont('Segoe UI',10))
    output=Path(__file__).parent/'images'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        settings=SettingsManager(Path(temp)/'config.json')
        settings.set('animations_enabled',False)
        settings.set('companion_style','starlight')
        db=DatabaseManager(Path(temp)/'preview.db')
        populate_demo(db,settings)
        with db._connection() as conn:
            RewardService.award(conn,'fixture:preview','Fictional preview',RULES.threshold(64))
        db.get_evolution_snapshot(claim_unlocks=True)
        dashboard=Dashboard(db,settings,FocusSessionManager())
        dashboard.show(); dashboard.navigate(3)
        for _ in range(200):
            if dashboard.evolution_controller.snapshot:
                break
            QTest.qWait(10)
        app.processEvents()
        dashboard.grab().save(str(output/'evolution-journey.png'))
        dashboard.resize(960,640); app.processEvents()
        dashboard.grab().save(str(output/'evolution-small.png'))
        dashboard.evolution_controller.close(); dashboard.close()
    sheet=QImage(1200,480,QImage.Format_ARGB32)
    sheet.fill(QColor('#F5F7F6'))
    painter=QPainter(sheet)
    pet=HumanCharacterWidget(); pet.resize(180,160); pet.set_motion_enabled(False)
    for i,stage in enumerate(STAGES):
        x,y=(i%5)*240,(i//5)*240
        pet.companion_style='starlight' if i%2 else 'orbit'
        pet.set_evolution(progress_for(RULES.threshold(i*10+6)))
        pet.set_pose(EmotionalPose.PROUD)
        painter.drawPixmap(x+30,y+12,pet.grab())
        painter.setPen(QColor('#20372D')); painter.setFont(QFont('Segoe UI',12,QFont.Bold))
        painter.drawText(QRectF(x,y+174,240,24),Qt.AlignCenter,stage.name)
        painter.setFont(QFont('Segoe UI',9)); painter.setPen(QColor('#627E6E'))
        painter.drawText(QRectF(x,y+202,240,24),Qt.AlignCenter,stage.accessory)
    painter.end()
    sheet.save(str(output/'evolution-cosmetics.png'))
    pet.close()
    print('Evolution screenshots saved in docs/images (fictional data only).')


if __name__=='__main__':
    main()
