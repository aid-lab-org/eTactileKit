import sys
import os
from PyQt5.QtWidgets import QMainWindow, QApplication
from views.mainwindow import MainWindow
from controllers.maincontroller import MainController

from sidebar_ui import Ui_MainWindow
class App(QMainWindow):
    def __init__(self):
        super(App, self).__init__()

        #Adding the ui to the main window
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #You can define the global variables for the app here
        self.initUI()

    def initUI(self):
        self.ui.icon_only_widget.hide()
        self.ui.home_btn_1.setChecked(True)
        self.ui.expand_btn_1.setChecked(True)
        self.setWindowTitle("EtactileKit Fabrication Tool")

        self.main_window = MainWindow(self)

        # # Initialize the main controller
        self.controller = MainController(self)

        # # Automatically resize the main window based on the screen size
        screen = QApplication.primaryScreen()
        available_rect = screen.availableGeometry() # Getting only the available screen geometry

        # Use the available geometry for the width and height
        window_width  = int(available_rect.width()  * 0.8)
        window_height = int(available_rect.height() * 0.8)

        # Set the geometry of the main window
        self.setGeometry(
        available_rect.x() + int(available_rect.width()  * 0.1),  # x position
        available_rect.y() + int(available_rect.height() * 0.1),  # y position
        window_width,
        window_height
        )
        
        # # Ensure a minimum size
        self.viewer_layout = self.ui.verticalLayout_14
        # Replace the widget
        if self.viewer_layout is not None:
            # Remove the existing viewer_widget
            self.viewer_layout.replaceWidget(self.ui.viewer_widget, self.main_window)
            # Hide or delete the old viewer_widget if necessary
            # self.ui.viewer_widget.hide()  # Optionally hide the original widget
            self.ui.viewer_widget.deleteLater()  # Or delete the old widget

        # Refresh the view to avoid visual defects
        self.repaint()  # Force a full repaint of the main window

def main():
    app = QApplication(sys.argv)
    # Get the directory where this script file is located
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Getting the path of the stylesheet
    style_path = os.path.join(BASE_DIR, "resources/stylesheets", "style.qss")
    # Reading the stylesheet
    with open(style_path, 'r') as style_file:
        style_str = style_file.read()
    app.setStyleSheet(style_str)

    main_window = App()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()  # Run the main function