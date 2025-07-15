from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy, QApplication
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QCursor

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        layout = QHBoxLayout()

        self.threed_button = self.create_button("3D Editor", 150, 150)
        self.pcb_button = self.create_button("PCB Generator", 150, 150)
        self.laser_cut_button = self.create_button("2D Layout Mode", 150, 150)

        layout.addWidget(self.laser_cut_button)
        layout.addWidget(self.pcb_button)
        layout.addWidget(self.threed_button)
               
        self.setLayout(layout)
    
    def create_button(self, text, sizex, sizey):
        # Create a button with the specified text and size
        button = QPushButton(text)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        button.setFont(font)
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setObjectName("mode_button")

        # Set size policy to make buttons scalable
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        base_button_size = QSize(500, 400)
        # Set the base size and minimum size for buttons
        button.setFixedSize(base_button_size)
        button.setMinimumSize(int(base_button_size.width() * 0.5), int(base_button_size.height() * 0.5))
        return button

        