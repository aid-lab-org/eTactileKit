import sys
from PyQt5.QtWidgets import QApplication, QMainWindow

from sidebar_ui import Ui_MainWindow
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.initUI()

    def initUI(self):
        self.ui.icon_only_widget.hide()
        self.ui.home_btn_1.setChecked(True)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    #loading the style file
    with open('3_FabricationTool_App/src/ui/style.qss', 'r') as style_file:
        style_str = style_file.read()
    app.setStyleSheet(style_str)


    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())