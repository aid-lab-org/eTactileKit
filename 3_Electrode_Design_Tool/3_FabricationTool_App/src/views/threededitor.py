import os
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QPushButton, QSlider, QLabel, QHBoxLayout, QSplitter, QSpacerItem, QSizePolicy, QProgressDialog, QLineEdit, QCheckBox, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import pyvista as pv
from pyvistaqt import QtInteractor
class ThreeDEditor(QWidget):
    def __init__(self, parent=None):
        super(ThreeDEditor, self).__init__(parent)

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
        self.sidebar_widget.setObjectName("sidebar_widget_3d_editor")

        splitter.addWidget(self.sidebar_widget)

        # Set initial sizes (make the viewer larger)
        splitter.setStretchFactor(0, 5)  # 5 parts for viewer
        splitter.setStretchFactor(1, 1)  # 1 part for sidebar

        #------------------------------------------------------- Mesh Operations ----------------------------------------------------        #
        self.mesh_operation_layout = QVBoxLayout()
        # Load mesh button
        self.load_mesh_button = QPushButton('Load Mesh', self)
        self.mesh_operation_layout.addWidget(self.load_mesh_button)

        # Slider for mesh simplification
        # Horizontal layout for slider label and value
        slider_layout = QHBoxLayout()
        self.slider_label = QLabel('Mesh Simplification', self)
        self.slider_label.setObjectName("slider_label")
        slider_layout.addWidget(self.slider_label)

        self.slider_value_label = QLabel('100%', self)  # Label to show current slider value
        self.slider_value_label.setObjectName("slider_value_label")
        slider_layout.addWidget(self.slider_value_label)

        # self.sidebar.addLayout(slider_layout)
        self.mesh_operation_layout.addLayout(slider_layout)

         # Slider itself
        self.simplify_slider = QSlider(Qt.Horizontal)
        self.simplify_slider.setMinimum(0)
        self.simplify_slider.setMaximum(100)
        self.simplify_slider.setValue(100)
        self.simplify_slider.setTickInterval(10)
        # self.sidebar.addWidget(self.simplify_slider)
        self.mesh_operation_layout.addWidget(self.simplify_slider)
        self.sidebar.addLayout(self.mesh_operation_layout)

         # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.sidebar.addItem(spacer)

                   #------------------------------------------------------- Electrode Parameters ----------------------------------------------------        #
        self.heading_electrodes = QLabel('Adjust Electrode Parameters', self)
        self.heading_electrodes.setObjectName("heading_electrodes")
        # Add image displaying the electrode layout and arrows
        self.image_label = QLabel(self)
        pixmap = QPixmap(f"{ICON_DIR}Layout_Parameters.png")  # Path to the electrode layout image
        # Scale the image to fit the widget (you can customize the target width/height)
        # scaled_pixmap = pixmap.scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Adjust width and height as needed
        scaled_pixmap = pixmap.scaled(int(600*scale_x), int(300*scale_y), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Set the image label size to the same size as the scaled image
        self.image_label.setFixedSize(scaled_pixmap.size())

        # Create a transparent container widget that allows absolute positioning of input boxes
        overlay_widget = QWidget(self.image_label)
        overlay_widget.setFixedSize(scaled_pixmap.size())  # Make the overlay the same size as the image

        # Input box for Electrode Diameter
        self.elec_diameter_input = QLineEdit(overlay_widget)
        self.elec_diameter_input.setText("1.5mm")  # Placeholder text
        self.elec_diameter_input.setFixedWidth(int(100*scale_x))  # Adjust as needed
        # self.elec_diameter_input.move(65, 155)  # Place the input box finely
        self.elec_diameter_input.move(int(65*scale_x), int(155*scale_y))      # Place the input box finely

        # Input box for Gap Between Electrodes
        self.elec_gap_input = QLineEdit(overlay_widget)
        self.elec_gap_input.setText("3mm")
        self.elec_gap_input.setFixedWidth(int(100*scale_x))        
        # self.elec_gap_input.move(185, 20)     # Place the second input box finely
        self.elec_gap_input.move(int(185*scale_x), int(20*scale_y))     # Place the second input box finely

        # Input box for Routing Trace Diameter
        self.trace_diameter_input = QLineEdit(overlay_widget)
        self.trace_diameter_input.setText("0.9mm")
        self.trace_diameter_input.setFixedWidth(int(100*scale_x))
        # self.trace_diameter_input.move(470, 52)     # Place the third input box finely
        self.trace_diameter_input.move(int(470*scale_x), int(52*scale_y))     # Place the third input box finely
    
        # Input box for Routing Trace Clearance
        self.trace_clearance_input = QLineEdit(overlay_widget)
        self.trace_clearance_input.setText("2mm")
        self.trace_clearance_input.setFixedWidth(int(100*scale_x))
        # self.trace_clearance_input.move(480, 180)     # Place the fourth input box finely
        self.trace_clearance_input.move(int(490*scale_x), int(180*scale_y))     # Place the fourth input box finely

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
        pixmap = QPixmap(f"{ICON_DIR}3D_Connector_Dimensions.png")  # Path to the electrode layout image
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

        # Input box for Electrode Diameter
        self.conn_diameter_input = QLineEdit(overlay_widget)
        self.conn_diameter_input.setText("2mm")     # Placeholder text
        self.conn_diameter_input.setFixedWidth(int(100*scale_x))  # Adjust as needed
        # self.conn_diameter_input.move(65, 160)      # Place the input box finely
        self.conn_diameter_input.move(int(85*scale_x), int(160*scale_y))     # Place the input box finely

        # Input box for Gap Between Electrodes
        self.conn_gap_input = QLineEdit(overlay_widget)
        self.conn_gap_input.setText("4mm")
        self.conn_gap_input.setFixedWidth(int(100*scale_x))
        # self.conn_gap_input.move(185, 25)        # Place the second input box finely
        self.conn_gap_input.move(int(250*scale_x), int(25*scale_y))        # Place the second input box finely

        # Create a wrapper layout to center-align the image label
        centered_layout = QVBoxLayout()
        centered_layout.addWidget(self.heading_connector, alignment=Qt.AlignCenter)
        centered_layout.addWidget(self.image_label_conn, alignment=Qt.AlignCenter)
    
         # Add the image and the overlay widget to the main layout
        self.sidebar.addLayout(centered_layout)
                    # ------------------------------------------------------------------------------------------------------------------------------        #
        # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 60, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)

        # Select faces button
        self.select_electrode_faces_button = QPushButton('Select Electrode Faces', self)
        self.sidebar.addWidget(self.select_electrode_faces_button)

        # Select connector faces button
        self.select_connector_faces_button = QPushButton('Select Connector Faces', self)
        self.sidebar.addWidget(self.select_connector_faces_button)

        # Finish selection button
        self.finish_selection_button = QPushButton('Create Connections', self)
        self.sidebar.addWidget(self.finish_selection_button)

         # Spacer to push the remaining buttons to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.sidebar.addItem(spacer)

        # Checkbox to enable/disable exporting all the meshes
        self.export_all_conductive_meshes_checkbox = QCheckBox('Export All Conductive Meshes', self)
        self.export_all_conductive_meshes_checkbox.setChecked(False)
        self.sidebar.addWidget(self.export_all_conductive_meshes_checkbox)

        # Save the edited mesh button
        self.export_mesh_button = QPushButton('Generate Output Files', self)
        self.sidebar.addWidget(self.export_mesh_button)
        self.export_mesh_button.setObjectName("export_mesh_btn")

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

class Viewer(QtInteractor):
    def __init__(self, parent):
        super().__init__(parent)

    def load_mesh_to_canvas(self, mesh):            
        self.clear()              #clear the view
        self.add_mesh(mesh, color='lightblue', show_edges=True, edge_color='black')
        self.reset_camera()       # Reset the camera position to fit the mesh in the view

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

    def save_camera_view(self):
        self.camera_position = self.camera_position

    def restore_camera_view(self):
        self.camera_position = self.camera_position