"""Interactive, keyboard-accessible evolution worlds drawn entirely with Qt."""
import math
from PySide6.QtCore import Qt, QPointF, QRectF, QVariantAnimation, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QComboBox, QProgressBar, QFrame)
from app.productivity.progression import STAGES, RULES, TOTAL_LEVELS, progress_for
from app.ui.character import HumanCharacterWidget
from app.character.emotions import EmotionalPose


def xp_text(value):
    digits = str(value)
    return f'{value:,}' if len(digits) < 10 else f'{digits[0]}.{digits[1:3]} × 10^{len(digits)-1}'


def session_text(session):
    return f"{session['date']} · {session['duration_seconds'] // 60} min · {session.get('note') or 'A small step forward'}"


def text_label(text='', size=13, color='#20372D'):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setStyleSheet(f'color: {color}; font-size: {size}px; background: transparent;')
    return label


class StageMap(QWidget):
    def __init__(self, details, parent=None):
        super().__init__(parent)
        self.progress = progress_for(0)
        self.stage_index = 0
        self.flash = 0.0
        self.setMinimumSize(340, 300)
        self.setAccessibleName('Evolution path: ten connected level nodes')
        self.nodes = []
        for level in range(1, 11):
            button = QPushButton(str(level), self)
            button.setFixedSize(42, 42)
            button.clicked.connect(lambda checked=False, n=level: details(n))
            self.nodes.append(button)
        self.pet = HumanCharacterWidget(self)
        self.pet.setFixedSize(64, 74)
        self.pet.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(1100)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.valueChanged.connect(self._flash)

    def _flash(self, value):
        self.flash = value
        self.update()

    def positions(self):
        # Two switchback rows remain readable at minimum dashboard width.
        return [QPointF(36 + (i if i < 5 else 9-i) * (self.width()-72)/4,
                        108 if i < 5 else 238) for i in range(10)]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place()

    def _place(self):
        points = self.positions()
        for button, point in zip(self.nodes, points):
            button.move(round(point.x()-21), round(point.y()-21))
        self.pet.setVisible(self.stage_index == self.progress.stage_index)
        p = points[self.progress.level-1]
        self.pet.move(round(p.x()-32), round(p.y()-94))

    def set_progress(self, progress, stage, style, motion):
        self.progress, self.stage_index = progress, stage
        self.pet.companion_style = style
        self.pet.set_evolution(progress)
        self.pet.set_motion_enabled(motion)
        self.pet.set_pose(EmotionalPose.PROUD)
        for i, button in enumerate(self.nodes):
            rank = stage * 10 + i + 1
            completed, available = rank <= progress.completed, rank == progress.global_level and not progress.mastered
            state = 'Completed' if completed else 'Available' if available else 'Locked'
            button.setEnabled(completed or available)
            button.setAccessibleName(f'{STAGES[stage].name} level {i+1}, {state}')
            button.setToolTip(f'{state} · {RULES.cost(rank)} XP to complete\n{RULES.threshold(rank):,} total XP completes this level')
            fill = '#F3D18C' if completed else STAGES[stage].color if available else '#273D48'
            ink = '#162E2B' if completed or available else '#8EA7AE'
            button.setStyleSheet(f'''QPushButton {{ background:{fill}; color:{ink}; border:2px solid {fill}; border-radius:21px; padding:0; font-size:14px; }}
                QPushButton:focus {{ border:2px solid white; }} QPushButton:hover {{ border:2px solid white; }}''')
        self._place()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        stage = STAGES[self.stage_index]
        color = QColor(stage.color)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor('#163A35'))
        gradient.setColorAt(1, QColor('#121C31'))
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(self.rect()), 18, 18)
        # Original vector terrain: hills, islands, citadels and aurora bands.
        for i in range(7):
            c = QColor(color); c.setAlpha(12 + i*2)
            p.setBrush(c)
            x = i * self.width()/6
            if self.stage_index % 10 in (2, 3, 6, 7):
                p.drawRoundedRect(QRectF(x-28, 40+(i%3)*18, 50, self.height()), 6, 6)
            elif self.stage_index % 10 in (1, 5, 8, 9):
                p.drawEllipse(QRectF(x-70, 120+(i%2)*40, 160, 30))
            else:
                path = QPainterPath(QPointF(x-100, self.height()))
                path.quadTo(x, -20+(i%3)*35, x+100, self.height())
                p.drawPath(path)
        points = self.positions()
        for i in range(9):
            p.setPen(QPen(QColor('#EACB8A' if self.stage_index*10+i+1 <= self.progress.completed else '#45606B'), 3, Qt.SolidLine, Qt.RoundCap))
            path = QPainterPath(points[i])
            mid = (points[i].y()+points[i+1].y())/2
            path.cubicTo(points[i].x(), mid, points[i+1].x(), mid, points[i+1].x(), points[i+1].y())
            p.drawPath(path)
        if self.flash:
            c = QColor(stage.color); c.setAlpha(round(self.flash*80))
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawRoundedRect(QRectF(self.rect()), 18, 18)

    def hideEvent(self, event):
        self.animation.stop()
        self.flash = 0
        super().hideEvent(event)


class JourneyPanel(QWidget):
    def __init__(self, controller, settings, parent=None):
        super().__init__(parent)
        self.controller, self.settings = controller, settings
        self.progress = progress_for(0)
        self._sessions = None
        self._selected_level = None
        self.celebration_timer = QTimer(self)
        self.celebration_timer.setSingleShot(True)
        self.celebration_timer.timeout.connect(lambda: self.pet.set_pose(EmotionalPose.PROUD))
        box = QVBoxLayout(self)
        box.setContentsMargins(0,0,0,0)
        box.setSpacing(16)
        box.addWidget(text_label('YOUR NEXT CHAPTER', 11, '#627E6E'))
        self.title = text_label('Seedling · Level 1 / 10', 28)
        box.addWidget(self.title)
        self.summary = text_label('One small session. A world of possibilities.', 13, '#627E6E')
        box.addWidget(self.summary)
        self.xp_bar = QProgressBar(); self.xp_bar.setRange(0,1000); self.xp_bar.setTextVisible(False)
        self.xp_bar.setFixedHeight(9)
        box.addWidget(self.xp_bar)
        navigation = QHBoxLayout()
        self.stage_picker = QComboBox()
        self.stage_picker.setAccessibleName('Explore evolution stages')
        for i, stage in enumerate(STAGES):
            self.stage_picker.addItem(f'{i+1:02d}   {stage.name} — {stage.landscape}', i)
        self.stage_picker.currentIndexChanged.connect(self._stage_changed)
        navigation.addWidget(self.stage_picker, 1)
        here = QPushButton('My stage'); here.clicked.connect(lambda: self.stage_picker.setCurrentIndex(self.progress.stage_index))
        navigation.addWidget(here)
        box.addLayout(navigation)
        center = QHBoxLayout(); center.setSpacing(16)
        self.map = StageMap(self._details)
        center.addWidget(self.map, 3)
        panel = QFrame(); panel.setObjectName('card'); panel.setMaximumWidth(240)
        side = QVBoxLayout(panel)
        self.pet = HumanCharacterWidget(); self.pet.setFixedSize(170,150)
        side.addWidget(self.pet, 0, Qt.AlignHCenter)
        self.reward = text_label('',16)
        side.addWidget(self.reward)
        self.next_unlock = text_label('',12,'#627E6E')
        side.addWidget(self.next_unlock)
        side.addStretch()
        center.addWidget(panel,1)
        box.addLayout(center)
        self.details = text_label('Select a level to see its progress and reward.',13)
        box.addWidget(self.details)
        box.addWidget(text_label('Recent accomplishments',17))
        self.rewards = text_label('',12,'#627E6E'); box.addWidget(self.rewards)
        box.addWidget(text_label('Your completed sessions · history preserved',16))
        self.list = QListWidget(); self.list.setAccessibleName('Completed sessions and notes')
        self.list.setMinimumHeight(150); self.list.setMaximumHeight(230)
        self.list.setStyleSheet('QListWidget { background:white; color:#20372D; border:1px solid #D5E3DB; border-radius:10px; padding:8px; } QListWidget::item { padding:8px; } QListWidget::item:selected { background:#DDF3E5; color:#193C2E; }')
        box.addWidget(self.list)
        controller.changed.connect(self._received)
        controller.advanced.connect(self.celebrate)
        if controller.snapshot:
            self._received(controller.snapshot)

    def _stage_changed(self):
        self._selected_level = None
        self.map.set_progress(self.progress, self.stage_picker.currentIndex(), self.settings.get('companion_style','orbit'), self.settings.get('animations_enabled',True))
        stage = STAGES[self.stage_picker.currentIndex()]
        self.details.setText(f'{stage.name} · {stage.landscape}. {stage.accessory} unlocks on entry. Complete each level to advance; levels 4 and 7 add visor and orbit details.')

    def _details(self, level):
        self._selected_level = level
        rank = self.stage_picker.currentIndex()*10+level
        state = 'Completed' if rank <= self.progress.completed else 'Your current level'
        self.details.setText(f'{STAGES[self.stage_picker.currentIndex()].name} · Level {level} · {state}. {RULES.cost(rank)} XP completes this level. '
                             + ('Visor trim unlocked here.' if level == 3 else 'Orbit details unlocked here.' if level == 6 else 'Next stage unlocks after this level.' if level == 10 and rank < TOTAL_LEVELS else 'Every step counts.'))

    def _received(self, snapshot):
        previous = self.progress
        self.progress = progress = snapshot['progress']
        self.title.setText(f'{progress.stage.name} · Level {progress.level} / 10')
        self.summary.setText(('Demo · fictional data · ' if self.settings.get('demo_mode',False) else '') + f'{xp_text(progress.xp)} earned XP · ' + ('Journey mastered. Your XP keeps growing.' if progress.mastered else f'{progress.earned} / {progress.required} XP to complete this level') + (' · previous level preserved' if progress.curve_credit else ''))
        self.xp_bar.setValue(1000 if progress.mastered else min(1000, progress.earned*1000//progress.required))
        self.xp_bar.setToolTip(f'Earned XP: {xp_text(progress.xp)}. Previous-level adjustment: {xp_text(progress.curve_credit)} XP.' if progress.curve_credit else 'Your earned XP moves this level forward. Each level takes a little more focus.')
        if previous.stage_index != progress.stage_index:
            self.stage_picker.setCurrentIndex(progress.stage_index)
        self.pet.companion_style = self.settings.get('companion_style','orbit')
        self.pet.set_evolution(progress)
        self.pet.set_motion_enabled(self.settings.get('animations_enabled',True))
        self.pet.set_pose(EmotionalPose.PROUD)
        self.reward.setText(progress.stage.accessory)
        upcoming = STAGES[min(len(STAGES)-1,progress.stage_index+1)]
        self.next_unlock.setText('Your celestial collection is complete. Keep making time for what matters.' if progress.mastered else
            f'Next: {upcoming.accessory} at {upcoming.name} 1.' if progress.stage_index < len(STAGES)-1 else f'Complete {STAGES[-1].name} 10 to master the journey.')
        self.map.set_progress(progress,self.stage_picker.currentIndex(),self.settings.get('companion_style','orbit'),self.settings.get('animations_enabled',True))
        if self._selected_level is not None:
            self._details(self._selected_level)
        sessions = snapshot['sessions']
        if sessions != self._sessions:
            self._sessions = sessions
            self.list.clear(); self.list.addItems([session_text(s) for s in sessions])
        self.rewards.setText('\n'.join(f"+{xp_text(int(r['xp']))} XP  ·  {r['kind']}" for r in snapshot['rewards'][:4]) or 'Your first completed focus session earns 25 XP. Tasks earn 10 XP once.')

    def celebrate(self, count):
        if self.settings.get('animations_enabled',True) and self.isVisible():
            self.map.animation.start()
            self.pet.set_pose(EmotionalPose.CELEBRATING)
            self.celebration_timer.start(3000)

    def hideEvent(self, event):
        self.celebration_timer.stop()
        self.pet.set_pose(EmotionalPose.PROUD)
        super().hideEvent(event)

    def refresh(self, db=None):
        self.controller.request()
