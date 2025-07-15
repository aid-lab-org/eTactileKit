from PyQt5.QtWidgets import QMessageBox

from views.mainwindow import MainWindow
from views.threededitor import ThreeDEditor
from controllers.threedcontroller import ThreeDController
from views.pcbeditor import PCBEditor
from controllers.pcbcontroller import PCBController
from views.lasercuteditor import LaserCutEditor
from controllers.lasercutcontroller import LaserCutController

class MainController:
    def __init__(self, app):
        self.app = app
        self.current_widget = self.app.main_window  # To keep track of the current widget

        # Connect signals from MainWindow buttons
        self.app.main_window.threed_button.clicked.connect(self.open_threed_editor)
        self.app.main_window.pcb_button.clicked.connect(self.open_pcb_generator)
        self.app.main_window.laser_cut_button.clicked.connect(self.laser_cut_generator)

        self.app.ui.home_btn_5.clicked.connect(self.confirm_return_to_main_menu)

    def replace_current_widget(self, new_widget):
        """Helper method to replace the current widget with a new one."""
        if self.current_widget:
            self.app.viewer_layout.replaceWidget(self.current_widget, new_widget)
            # self.current_widget.hide()  # Optionally hide the old widget
            self.current_widget.deleteLater()  # Clean up the old widget

        self.current_widget = new_widget
        self.app.repaint()  # Refresh the UI to prevent visual glitches

    def open_threed_editor(self):
        threed_editor = ThreeDEditor(self.app)
        self.threed_controller = ThreeDController(threed_editor) # Instantiate the controller and pass the view

        self.replace_current_widget(threed_editor)
        self.app.ui.collapse_btn_1.clicked.connect(threed_editor.sidebar_widget.setHidden)
        self.app.ui.expand_btn_1.clicked.connect(threed_editor.sidebar_widget.setVisible)
        # Apply styles to the new widget if needed
        # threed_editor.setStyleSheet(self.app.styleSheet())  # Reapply stylesheet if needed

    def open_pcb_generator(self):
        pcb_editor = PCBEditor(self.app)
        self.pcb_controller = PCBController(pcb_editor)
 
        self.replace_current_widget(pcb_editor)
        self.app.ui.collapse_btn_1.clicked.connect(pcb_editor.sidebar_widget.setHidden)
        self.app.ui.expand_btn_1.clicked.connect(pcb_editor.sidebar_widget.setVisible)

    def laser_cut_generator(self):
        lasercuteditor = LaserCutEditor(self.app)
        self.lasercut_controller = LaserCutController(lasercuteditor)

        self.replace_current_widget(lasercuteditor)
        self.app.ui.collapse_btn_1.clicked.connect(lasercuteditor.sidebar_widget.setHidden)
        self.app.ui.expand_btn_1.clicked.connect(lasercuteditor.sidebar_widget.setVisible)

    def confirm_return_to_main_menu(self):
        reply = QMessageBox.question(self.app, 'Confirm Return', 
                                     'Are you sure you want to discard current design?', 
                                     QMessageBox.Yes | QMessageBox.No, 
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Create a new instance of MainMenu when returning to the main menu
            new_main_window = MainWindow(self.app)
            self.replace_current_widget(new_main_window)
            
            # Reconnect signals for the new MainWindow instance
            new_main_window.pcb_button.clicked.connect(self.open_pcb_generator)
            new_main_window.threed_button.clicked.connect(self.open_threed_editor)
            new_main_window.laser_cut_button.clicked.connect(self.laser_cut_generator)
