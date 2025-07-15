import os
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QSplitter, QSpacerItem, QSizePolicy, QLabel, QLineEdit, QProgressDialog, QDialog, QGridLayout, QStyle, QApplication
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
class PCBEditor(QWidget):
    def __init__(self, parent=None):
        super(PCBEditor, self).__init__(parent)
        pv.global_theme.allow_empty_mesh = True # Allow empty meshes to be displayed (slider values of 0)
        self.initUI()

    def initUI(self):
        # Get the directory where this script file is located
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # Getting the directory of the icons
        ICON_DIR = os.path.join(BASE_DIR, "../resources/icons/")  # Path to the icons directory

        # calculate the scale factor based on the current screen size
        screen = QApplication.primaryScreen()
        # available_rect = screen.availableGeometry() # Getting only the available screen geometry
        # x_size, y_size = available_rect.width(), available_rect.height()  # Current screen size
        x_size, y_size = screen.size().width(), screen.size().height()  # Current screen size
        x_orig, y_orig = 3840, 2088 # Developers original screen size
        scale_x, scale_y = x_size/x_orig, y_size/y_orig

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # Create a splitter to manage the space between the viewer and the sidebar
        splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(splitter)

        # Initialize the Viewer class (which is now also a QtInteractor)
        self.plotter = Viewer(self)
        splitter.addWidget(self.plotter)

        # Sidebar for controls
        self.sidebar_widget = QWidget()
        self.sidebar = QVBoxLayout(self.sidebar_widget)
        self.sidebar_widget.setObjectName("sidebar_widget_pcb_editor")

        splitter.addWidget(self.sidebar_widget)

        # Set initial sizes (make the viewer larger)
        splitter.setStretchFactor(0, 5)  # 5 parts for viewer
        splitter.setStretchFactor(1, 1)  # 1 part for sidebar

        # ----------------------------------------- Layout for uilities -------------------------------------------------------------------------
        self.utilities_layout = QHBoxLayout()
        self.sidebar.addLayout(self.utilities_layout)

        # Button to trigger image import
        self.restore_top_button = QPushButton('Show Top View', self)
        self.restore_top_button.clicked.connect(self.plotter.set_top_view)
        self.utilities_layout.addWidget(self.restore_top_button)

        # Button to trigger image import
        self.eraser_button = QPushButton('Eraser', self)
        self.utilities_layout.addWidget(self.eraser_button)

        # Button to clear the drawn elements on the canvas (electrodes, connectors, traces)
        self.clear_drawings_button = QPushButton('Clear All', self)
        self.utilities_layout.addWidget(self.clear_drawings_button)
        #----------------------------------------- Layout for buttons -------------------------------------------------------------------------

        # Butoon to trigger image import
        self.load_image_button = QPushButton('Load Base Image', self)
        self.sidebar.addWidget(self.load_image_button)

        # Button to calibrate dimensions
        self.calibrate_button = QPushButton('Calibrate Image Dimensions')
        self.sidebar.addWidget(self.calibrate_button)

        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)

        # Button to process Image
        self.extract_edges_button = QPushButton('Capture Image Edges')
        self.sidebar.addWidget(self.extract_edges_button)

                    #------------------------------------ Layout for show and hide buttons -------------------------------------
        self.show_hide_layout = QHBoxLayout()
        self.sidebar.addLayout(self.show_hide_layout)

        # Button to trigger image import
        self.show_image_button = QPushButton('Show Image', self)
        self.show_hide_layout.addWidget(self.show_image_button)

        # Button to trigger image import
        self.hide_image_button = QPushButton('Hide Image', self)
        self.show_hide_layout.addWidget(self.hide_image_button)
                    #-----------------------------------------------------------------------------------------------------------
        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)

                    #------------------------------------------------------- Electrode Parameters ----------------------------------------------------        #
        self.heading_electrodes = QLabel('Adjust Electrode Parameters', self)
        self.heading_electrodes.setObjectName("heading_electrodes")
        # Add image displaying the electrode layout and arrows
        self.image_label = QLabel(self)
        pixmap = QPixmap(f"{ICON_DIR}Layout_Parameters.png")  # Path to the electrode layout image
        # Scale the image to fit the widget (you can customize the target width/height)
        # scaled_pixmap = pixmap.scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Adjust width and height as needed
        scaled_pixmap = pixmap.scaled(int(600*scale_x), int(300*scale_y), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # Adjust width and height as needed
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Set the image label size to the same size as the scaled image
        self.image_label.setFixedSize(scaled_pixmap.size())

        # Create a transparent container widget that allows absolute positioning of input boxes
        overlay_widget = QWidget(self.image_label)
        overlay_widget.setFixedSize(scaled_pixmap.size())  # Make the overlay the same size as the image

        # Input box for Electrode Diameter
        self.diameter_input = QLineEdit(overlay_widget)
        self.diameter_input.setText("1.5mm")  # Placeholder text
        self.diameter_input.setFixedWidth(int(100*scale_x))  # Adjust as needed
        # self.diameter_input.move(65, 155)      # Place the input box finely
        self.diameter_input.move(int(65*scale_x), int(155*scale_y))      # Place the input box finely

        # Input box for Gap Between Electrodes
        self.gap_input = QLineEdit(overlay_widget)
        self.gap_input.setText("3mm")
        self.gap_input.setFixedWidth(int(100*scale_x))        
        # self.gap_input.move(185, 20)             # Place the second input box finely
        self.gap_input.move(int(185*scale_x), int(20*scale_y))             # Place the second input box finely

        # Input box for Trace Width
        self.trace_width = QLineEdit(overlay_widget)
        self.trace_width.setText("0.127mm")
        self.trace_width.setFixedWidth(int(120*scale_x))        
        # self.trace_width.move(475, 50)     # Place the second input box finely
        self.trace_width.move(int(475*scale_x), int(50*scale_y))     # Place the second input box finely

        # Input box for Routing clearance
        self.routing_clearance = QLineEdit(overlay_widget)
        self.routing_clearance.setText("0.4mm")
        self.routing_clearance.setFixedWidth(int(100*scale_x))        
        # self.routing_clearance.move(490, 180)     # Place the second input box finely
        self.routing_clearance.move(int(490*scale_x), int(180*scale_y))     # Place the second input box finely

        # Create a wrapper layout to center-align the image label
        centered_layout = QVBoxLayout()
        centered_layout.addWidget(self.heading_electrodes, alignment=Qt.AlignCenter)
        centered_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
    
        # Add the image and the overlay widget to the main layout
        self.sidebar.addLayout(centered_layout)
                    # ---------------------------------------------------------- Connector Parameters -------------------------------------------------        #
        self.heading_connector = QLabel('Connector Parameters', self)
        self.heading_connector.setObjectName("heading_connector")
        # Add image displaying the electrode layout and arrows
        self.image_label_conn = QLabel(self)
        pixmap = QPixmap(f"{ICON_DIR}PCB_Connector_Dimensions")  # Path to the electrode layout image
        # Scale the image to fit the widget (you can customize the target width/height)
        # scaled_pixmap = pixmap.scaled(500, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Adjust width and height as needed
        scaled_pixmap = pixmap.scaled(int(500*scale_x), int(300*scale_y), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.image_label_conn.setPixmap(scaled_pixmap)
        self.image_label_conn.setAlignment(Qt.AlignCenter)

        # Set the image label size to the same size as the scaled image
        self.image_label_conn.setFixedSize(scaled_pixmap.size())

        # Create a transparent container widget that allows absolute positioning of input boxes
        overlay_widget = QWidget(self.image_label_conn)
        overlay_widget.setFixedSize(scaled_pixmap.size())  # Make the overlay the same size as the image

        # Input box for Holding pad width
        self.holding_pad_width = QLineEdit(overlay_widget)
        self.holding_pad_width.setText("1.8mm")  # Placeholder text
        self.holding_pad_width.setFixedWidth(int(100*scale_x)) # Adjust as needed
        # self.holding_pad_width.move(50, 140)     # Place the input box finely
        self.holding_pad_width.move(int(50*scale_x), int(140*scale_y))     # Place the input box finely

        # Input box for holding pad height
        self.holding_pad_height = QLineEdit(overlay_widget)
        self.holding_pad_height.setText("2.2mm")
        self.holding_pad_height.setFixedWidth(int(100*scale_x))
        # self.holding_pad_height.move(60, 220)     # Place the second input box finely
        self.holding_pad_height.move(int(60*scale_x), int(220*scale_y))     # Place the second input box finely

        # Input box for Connector pad Width
        self.pad_width = QLineEdit(overlay_widget)
        self.pad_width.setText("0.6mm")  # Placeholder text
        self.pad_width.setFixedWidth(int(100*scale_x))  # Adjust as needed
        # self.pad_width.move(155, 0)  # Place the input box finely
        self.pad_width.move(int(155*scale_x), int(0*scale_y))

        # Input box for Connector Pad Height
        self.pad_height = QLineEdit(overlay_widget)
        self.pad_height.setText("1.3mm")
        self.pad_height.setFixedWidth(int(100*scale_x))
        # self.pad_height.move(65, 80)     # Place the second input box finely
        self.pad_height.move(int(65*scale_x), int(80*scale_y))     # Place the second input box finely

        # Input box for Gap Between Connector Pads
        self.pad_spacing = QLineEdit(overlay_widget)
        self.pad_spacing.setText("0.4mm")
        self.pad_spacing.setFixedWidth(int(100*scale_x))
        # self.pad_spacing.move(245, 143)   # Place the second input box finely
        self.pad_spacing.move(int(245*scale_x), int(143*scale_y))   # Place the second input box finely

        # Input box for Number of Connector Pads
        self.num_pads = QLineEdit(overlay_widget)
        self.num_pads.setText("16")
        self.num_pads.setFixedWidth(int(100*scale_x))
        # self.num_pads.move(280, 190)     # Place the second input box finely
        self.num_pads.move(int(280*scale_x), int(190*scale_y))     # Place the second input box finely

        # Create a wrapper layout to center-align the image label
        centered_layout = QVBoxLayout()
        centered_layout.addWidget(self.heading_connector, alignment=Qt.AlignCenter)
        centered_layout.addWidget(self.image_label_conn, alignment=Qt.AlignCenter)
    
         # Add the image and the overlay widget to the main layout
        self.sidebar.addLayout(centered_layout)
                    # ----------------------------------------------------------------------------------------------------------------------------------------        #

        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)
        
        # Button to start drawing regions for electrodes
        self.draw_electrode_regions_button = QPushButton('Draw New Electrode Regions')
        self.sidebar.addWidget(self.draw_electrode_regions_button)

        # Button to start drawing the connector pads
        self.draw_connector_regions_button = QPushButton('Draw Connector Lines')
        self.sidebar.addWidget(self.draw_connector_regions_button)

        # Button to adjust element modifications
        self.adjust_drawn_elements = QPushButton('Adjust Drawn Elements')
        self.sidebar.addWidget(self.adjust_drawn_elements)
        #define the adjust dialog
        self.adjust_dialog = AdjustElementsDialog(self)

        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)

        #Button to start manual routing
        self.route_manual_connection = QPushButton('Manual Route Connection')
        self.sidebar.addWidget(self.route_manual_connection)

        #Button to generate conductive traces
        self.route_automatic_connections = QPushButton('Auto Route Connections')
        self.sidebar.addWidget(self.route_automatic_connections)

        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)
        
        #Button to generate output files
        self.generate_output_files_button = QPushButton('Generate Output Files')
        self.sidebar.addWidget(self.generate_output_files_button)
        self.generate_output_files_button.setObjectName("generate_output_files_btn")

    def show_warning(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(message)
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def show_progress_window(self):
        # Show the progress dialog
        progress_dialog = QProgressDialog("Generating routing paths...", "Cancel", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setWindowTitle("Please Wait")
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() | Qt.CustomizeWindowHint)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        return progress_dialog
    
    def get_confirmation(self, title, message):
        # Create a question dialog
        reply = QMessageBox.question(
            self,                               # parent widget (could be None if you prefer)
            title,                              # dialog title
            message,                            # message text
            QMessageBox.Yes | QMessageBox.No    # buttons to display
        )
        return reply == QMessageBox.Yes

class Viewer(QtInteractor):
    def __init__(self, parent):
        super().__init__(parent)

        # Add a text actor to the scene
        self.add_text(
                    "Mode: Default",          # text to display
                    position='upper_right',     # or 'upper_right', (x, y) tuple, etc.
                    font_size=20,
                    color='red',               # text color
                    name="mode_label"          # optional name
                    )

    def load_image_to_canvas(self, plane, image):            
        self.clear() #clear the view
        self.add_mesh(plane, texture=image)

    def update_display(self, mesh = None, _color='lightblue', _show_edges=True, _edge_color='black', _opacity=1):
        """
        Clear the existing view and add new meshes to the display view.
        mesh: mesh to be displayed
        """
        self.clear()
        if mesh:
            self.add_mesh(mesh, color = _color, show_edges = _show_edges, edge_color = _edge_color, opacity = _opacity)

    def append_display(self, mesh = None, _color='lightblue', _show_edges=True, _edge_color='black', _opacity=1):
        """
        Append a mesh to the current display without changing the current elements.
        mesh: mesh to be added to the siplay
        """
        if mesh:
            self.add_mesh(mesh, color = _color, show_edges = _show_edges, edge_color = _edge_color, opacity = _opacity)
    def set_top_view(self):
        self.camera_position = 'xy'

    def save_camera_view(self):
        self.camera_position = self.camera_position

    def restore_camera_view(self):
        self.camera_position = self.camera_position
    
    def set_operation_mode(self, mode):
        self.add_text(f"Mode: {mode}",
                    position='upper_right',
                    font_size=20,
                    color='red',
                    name="mode_label",
                    )
    
class AdjustElementsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_closable = True
        self.setWindowTitle("Adjust Drawn Elements")
        self.setObjectName("adjust_elements_dialog")

        # ------------------------------
        # 1) Top: "Select Elements" Button
        # ------------------------------
        self.select_elements_to_move = QPushButton("Select Elements to Move")
        self.select_elements_to_move.setAutoDefault(False)  # Make it the default button

        # ------------------------------
        # 2) Middle Left: 5-Button Layout (Arrows + Reset)
        # ------------------------------
        self.arrow_up_button = QPushButton()
        self.arrow_up_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.arrow_up_button.setAutoDefault(False)  # Make it the default button

        self.arrow_down_button = QPushButton()
        self.arrow_down_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.arrow_down_button.setAutoDefault(False)  # Make it the default button

        self.arrow_left_button = QPushButton()
        self.arrow_left_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        self.arrow_left_button.setAutoDefault(False)

        self.arrow_right_button = QPushButton()
        self.arrow_right_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.arrow_right_button.setAutoDefault(False)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setAutoDefault(False)

        # Place them in a 3×3 or 3×3-like grid
        grid_layout = QGridLayout()
        # Row 0:    [ empty,      Up,       empty ]
        # Row 1:    [ Left,   Reset, Right ]
        # Row 2:    [ empty,    Down,     empty ]
        # But we'll just skip corners if we want a tight cross shape

        grid_layout.addWidget(self.arrow_up_button,    0, 1)
        grid_layout.addWidget(self.arrow_left_button,  1, 0)
        grid_layout.addWidget(self.reset_button,       1, 1)
        grid_layout.addWidget(self.arrow_right_button, 1, 2)
        grid_layout.addWidget(self.arrow_down_button,  2, 1)

        # ------------------------------
        # 3) Middle Right: Step & Angle & confirm
        # ------------------------------
        self.step_size_label = QLabel("Step Size:")
        self.step_size_input = QLineEdit()
        self.step_size_input.setText("1.0mm")
        # self.step_size_input.setValidator(QDoubleValidator())  # allow floats only

        self.angle_label = QLabel("Rotation Angle:")
        self.angle_input = QLineEdit()
        self.angle_input.setText("0°")
        # self.angle_input.setValidator(QDoubleValidator())

        self.confirm_transformation_button = QPushButton("Confirm Transformation")
        self.confirm_transformation_button.setAutoDefault(False)

        # Put step size and angle in a vertical layout
        vbox_params = QVBoxLayout()
        vbox_params.addWidget(self.step_size_label)
        vbox_params.addWidget(self.step_size_input)
        vbox_params.addSpacing(10)
        vbox_params.addWidget(self.angle_label)
        vbox_params.addWidget(self.angle_input)
        vbox_params.addSpacing(10)
        vbox_params.addWidget(self.confirm_transformation_button)
        vbox_params.addStretch(1)  # push them up

        # Combine the 5-button layout (left) and the two text boxes (right)
        hbox_middle = QHBoxLayout()
        hbox_middle.addLayout(grid_layout)
        hbox_middle.addSpacing(20)
        hbox_middle.addLayout(vbox_params)

        # ------------------------------
        # Overall Layout
        # ------------------------------
        main_layout = QVBoxLayout()
        # Top button
        main_layout.addWidget(self.select_elements_to_move, alignment=Qt.AlignLeft)
        main_layout.addSpacing(10)
        # Middle controls
        main_layout.addLayout(hbox_middle)
        main_layout.addStretch(1)

        self.setLayout(main_layout)

        # # (Optionally) set a fixed size or let it be resizable
        # # self.setFixedSize(500, 400)
        # handling the close event signals within the editor
        self.select_elements_to_move.clicked.connect(self.set_not_closable)
        self.confirm_transformation_button.clicked.connect(self.set_closable)

    def set_closable(self):
        self.is_closable = True
    
    def set_not_closable(self):
        self.is_closable = False

    def closeEvent(self, event):
        if self.is_closable:
            event.accept()
        else:  
            reply = QMessageBox.question(
                self,
                "Task Incomplete",
                "Please press confirm transform to finalize changes.\nDo you want to close anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

