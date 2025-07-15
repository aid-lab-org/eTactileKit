import os
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QApplication
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QMouseEvent, QCursor

import pyvista as pv
from shapely.geometry import Point, Polygon, LineString
from shapely.affinity import translate, rotate
import numpy as np
from scipy.signal import savgol_filter
import cv2
from vtk import vtkCellPicker
import heapq
import math


from utils.helpers import (
    get_arc_point,
    draw_arc,
    # rotate,
    # translate,
    flip_y,
    flip_x,
    optimize_points,
    chaikin,
    rotate_point,
    scale,
)
from utils.pcb_json import (
    dump_json,
    plot_json,
    create_via,
    create_rectangular_pad,
    create_circular_pad,
    create_pin,
    create_silk,
    create_mounting_hole,
)

class PCBController:
    def __init__(self, ui_page):
        self.ui_page = ui_page

        self.ui_page.eraser_button.clicked.connect(self.toggle_eraser_mode)
        self.ui_page.clear_drawings_button.clicked.connect(self.clear_all_drawings)
        self.ui_page.load_image_button.clicked.connect(self.load_image)
        self.ui_page.calibrate_button.clicked.connect(self.enable_dimensions_calibrate_mode)
        self.ui_page.extract_edges_button.clicked.connect(self.extract_edges)
        self.ui_page.show_image_button.clicked.connect(self.enable_image_view)
        self.ui_page.hide_image_button.clicked.connect(self.disable_image_view)
        self.ui_page.draw_electrode_regions_button.clicked.connect(self.enable_electrode_region_drawing)
        self.ui_page.draw_connector_regions_button.clicked.connect(self.enable_connector_region_drawing)
        self.ui_page.route_manual_connection.clicked.connect(self.enable_manual_routing_mode)
        self.ui_page.route_automatic_connections.clicked.connect(self.generate_conductive_traces)
        self.ui_page.generate_output_files_button.clicked.connect(self.generate_output_files)
        self.ui_page.adjust_drawn_elements.clicked.connect(self.show_adjust_dialog)
        # Connect signals from the pop-up dialog
        self.ui_page.adjust_dialog.select_elements_to_move.clicked.connect(self.enable_element_adjustment)
        self.ui_page.adjust_dialog.arrow_up_button.clicked.connect(self.adjust_up)
        self.ui_page.adjust_dialog.arrow_down_button.clicked.connect(self.adjust_down)
        self.ui_page.adjust_dialog.arrow_left_button.clicked.connect(self.adjust_left)
        self.ui_page.adjust_dialog.arrow_right_button.clicked.connect(self.adjust_right)
        self.ui_page.adjust_dialog.reset_button.clicked.connect(self.reset_transform)
        self.ui_page.adjust_dialog.confirm_transformation_button.clicked.connect(self.finalize_element_adjustment)

        # Connect signals from the UI for the PCB editor-text boxes
        self.ui_page.diameter_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.gap_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.trace_width.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.routing_clearance.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.holding_pad_width.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.holding_pad_height.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.pad_width.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.pad_height.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.pad_spacing.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.num_pads.editingFinished.connect(lambda: self.update_parameters())
        # Connect text boxes from the pop-up dialog
        self.ui_page.adjust_dialog.step_size_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.adjust_dialog.angle_input.editingFinished.connect(lambda: self.update_parameters())

        # Intialize Variable to show the current operating mode
        self.current_mode = None

        # Intitialize variables for handling erasing
        self.eraser_mode = False

        # Initialize variable for handlin image import
        self.base_image = None
        self.image_plane = None
        self.texture = None
        self.show_image = True

        # Initialize variables for dimension calibration
        self.calibrate_dimensions_mode = False
        self.calibration_start_point = None
        self.calibration_end_point = None
        self.scale_factor = 1.0 # Default scale factor for image dimensions

        # Initialize to track drawing contours
        self.is_region_drawing_mode = False
        self.is_drawing = False
        self.drawing_points = []
        
        #Initialize variables for image processing and edge extraction
        self.extracted_edge_contour_points = []
        
        self.drawn_contour_points = []       #stores array of the manually drawn contour of the image edge (NOT USED NOW)
        self.image_edge_drawing_mode = False #NOT USED NOW
        
        # Intitialize variables for electrodes
        self.electrode_region_drawing_mode = False
        self.populated_electrode_points = []
        self.electrode_radius = self.read_parameter_mm(self.ui_page.diameter_input)/2# default value is 0.75mm
        self.electrode_gap = self.read_parameter_mm(self.ui_page.gap_input) # default value is 3.0

        # Initialize variables for connector lines
        self.connector_region_drawing_mode = False
       
        self.holding_pad_width = self.read_parameter_mm(self.ui_page.holding_pad_width) #default value is 1.65mm
        self.holding_pad_height = self.read_parameter_mm(self.ui_page.holding_pad_height) #default value is 1.3mm
        self.pad_height = self.read_parameter_mm(self.ui_page.pad_height) #default value is 1mm
        self.pad_width = self.read_parameter_mm(self.ui_page.pad_width) #default value is 0.3mm
        self.pad_spacing = self.read_parameter_mm(self.ui_page.pad_spacing) #default value is 1mm
        self.num_pads = int(self.read_parameter_mm(self.ui_page.num_pads)) #default value is 16mm

        self.connector_segments = []        #line segments to create a connector footprint
        self.connector_pads_data = []       #group data for the pads of the connector 
        self.connector_polygons_data = []   #group data for the polygons of the connector pads

        self.ground_pad_info = []           #stores the ground pad information seperately
        self.connector_pad_info = []        #stores the connector pad information seperately

        # # Initialize variables for tracks and routing
        self.track_width = self.read_parameter_mm(self.ui_page.trace_width) #default value is 0.127mm
        self.routing_clearance = self.read_parameter_mm(self.ui_page.routing_clearance) #default value is 0.127mm
        self.routing_paths = []

        self.manual_routing_mode = False
        self.manual_routing_start_type = None #stores the type of the starting point of the manual routing 'electrode' or 'connector'
        self.manual_routing_points = []  #Contains the routing points temporarily for a single manual routing path

        # Initialize variables to adjust element positions
        self.adjust_elements_region_drawing_mode = False
        self.elements_available_to_adjust = False
        self.total_adjust_element_x = 0 #variable to keep track of x adjustment
        self.total_adjust_element_y = 0 #variable to keep track of y adjustment
        self.adjust_step_size = self.read_parameter_mm(self.ui_page.adjust_dialog.step_size_input) #default value is 1mm
        self.adjust_element_rotation = self.read_parameter_degree(self.ui_page.adjust_dialog.angle_input) #default value is 0°
        self.adjusted_electrode_points = [] #stores the electrode points that are being adjusted
        self.original_electrode_points_to_adjust = [] #stores the original electrode points before adjustment
        self.adjusted_electrode_actors = [] #stores the actors of the adjusted electrodes in the plotter

        # Connect interactor event
        self.ui_page.plotter.iren.add_observer("LeftButtonPressEvent", self.on_left_button_press)
        self.ui_page.plotter.iren.add_observer("MouseMoveEvent", self.on_mouse_move)
        self.ui_page.plotter.iren.add_observer("LeftButtonReleaseEvent", self.on_left_button_release)

    def read_parameter_mm(self, line_edit):
        #get the updated parameters from the UI
        try:
            value =  float(line_edit.text().strip("mm"))
            return value
        except:
            self.ui_page.show_warning("Invalid Input!. Please enter a valid numerical value for the parameter")
            return None
        
    def read_parameter_degree(self, line_edit):
        #get the updated parameters from the UI
        try:
            value =  -float(line_edit.text().strip("°"))
            return value
        except:
            self.ui_page.show_warning("Invalid Input!. Please enter a valid numerical value for the parameter")
            return None
    
    def update_parameters(self):
        #get the electrode radius
        in_value = self.read_parameter_mm(self.ui_page.diameter_input)
        if in_value is not None:
            self.electrode_radius = in_value/2
        else:
            self.ui_page.diameter_input.setText(str(self.electrode_radius*2) + "mm")
        #get the electrode spacing
        in_value = self.read_parameter_mm(self.ui_page.gap_input)
        if in_value is not None:
            self.electrode_spacing = in_value
        else:
            self.ui_page.gap_input.setText(str(self.electrode_spacing) + "mm")
        #get the trace width
        in_value = self.read_parameter_mm(self.ui_page.trace_width)
        if in_value is not None:
            self.track_width = in_value
        else:
            self.ui_page.trace_width.setText(str(self.track_width) + "mm")
        #get the routing clearance
        in_value = self.read_parameter_mm(self.ui_page.routing_clearance)
        if in_value is not None:
            self.routing_clearance = in_value
        else:
            self.ui_page.routing_clearance.setText(str(self.routing_clearance) + "mm")
        #get the holding pad width
        in_value = self.read_parameter_mm(self.ui_page.holding_pad_width)
        if in_value is not None:
            self.holding_pad_width = in_value
        else:
            self.ui_page.holding_pad_width.setText(str(self.holding_pad_width) + "mm")
        #get the holding pad height
        in_value = self.read_parameter_mm(self.ui_page.holding_pad_height)
        if in_value is not None:
            self.holding_pad_height = in_value
        else:
            self.ui_page.holding_pad_height.setText(str(self.holding_pad_height) + "mm")
        #get the pad width
        in_value = self.read_parameter_mm(self.ui_page.pad_width)
        if in_value is not None:
            self.pad_width = in_value
        else:
            self.ui_page.pad_width.setText(str(self.pad_width) + "mm")
        #get the pad height
        in_value = self.read_parameter_mm(self.ui_page.pad_height)
        if in_value is not None:
            self.pad_height = in_value
        else:
            self.ui_page.pad_height.setText(str(self.pad_height) + "mm")
        #get the pad spacing
        in_value = self.read_parameter_mm(self.ui_page.pad_spacing)
        if in_value is not None:
            self.pad_spacing = in_value
        else:
            self.ui_page.pad_spacing.setText(str(self.pad_spacing) + "mm")
        #get the number of pads
        in_value = self.read_parameter_mm(self.ui_page.num_pads)
        if in_value is not None:
            self.num_pads = int(in_value)
        else:
            self.ui_page.num_pads.setText(str(self.num_pads))
        #get the adjust step size
        in_value = self.read_parameter_mm(self.ui_page.adjust_dialog.step_size_input)
        if in_value is not None:
            self.adjust_step_size = in_value
        else:
            self.ui_page.adjust_dialog.step_size_input.setText(str(self.adjust_step_size) + "mm")
        #get the rotation angle
        in_value = self.read_parameter_degree(self.ui_page.adjust_dialog.angle_input)
        if in_value is not None:
            self.adjust_element_rotation = in_value
            #update the angle adjustment in the plotter
            self.transform_adjustable_electrodes()
        else:
            self.ui_page.adjust_dialog.angle_input.setText(str(self.adjust_element_rotation) + "°")

    # ----------------------------------------RESET MODES AND DATA -----------------------------------------
    def reset_modes(self):
        #disable the eraser mode
        self.eraser_mode = False
        self.ui_page.plotter.setCursor(Qt.ArrowCursor) # Reset cursor to defaults
        #disable the calibration mode
        self.calibrate_dimensions_mode = False
        #disable electrode, connector and image edge region drawing modes
        self.electrode_region_drawing_mode = False
        self.connector_region_drawing_mode = False
        self.image_edge_drawing_mode = False
        self.is_region_drawing_mode = False
        self.is_drawing = False
        #disable the manual routing mode
        self.manual_routing_mode = False
        #disable the adjust elements mode
        self.adjust_elements_region_drawing_mode = False
        self.elements_available_to_adjust = False

    def reset_all_data(self):
        #reset all the image data
        self.base_image = None
        self.image_plane = None
        self.texture = None
        self.show_image = True
        #reset all the calibration data
        self.scale_factor = 1.0
        #reset all the edge extraction data
        self.extracted_edge_contour_points = []
        self.drawn_contour_points = []
        #reset all the electrode data
        self.populated_electrode_points = []
        #reset all the connector data
        self.connector_segments = []
        self.connector_pads_data = []
        self.connector_polygons_data = []
        self.ground_pad_info = []
        self.connector_pad_info = []
        #reset all the routing data
        self.routing_paths = []
        self.manual_routing_start_type = None
        self.manual_routing_points = []
        self.update_display_content()
        #reset all the adjust elements data
        self.adjusted_electrode_points = []
        self.original_electrode_points_to_adjust = []
        self.adjusted_electrode_actors = []

    def clear_all_drawings(self):
        if self.ui_page.get_confirmation("Clear all the drawn elements","Are you sure you want to clear all drawn elements?") == False:
            return
        #reset all the modes if any are existing
        self.reset_modes()
        #reset all the data except the eimage and edge data
        #reset all the electrode data
        self.populated_electrode_points = []
        #reset all the connector data
        self.connector_segments = []
        self.connector_pads_data = []
        self.connector_polygons_data = []
        self.ground_pad_info = []
        self.connector_pad_info = []
        #reset all the routing data
        self.routing_paths = []
        self.manual_routing_start_type = None
        self.manual_routing_points = []
        #reset all the adjust elements data
        self.adjusted_electrode_points = []
        self.original_electrode_points_to_adjust = []
        self.adjusted_electrode_actors = []
        self.update_display_content()
    
    # ------------------------------------------- FILE HANDLING -----------------------------------------------------------------------------
    def load_image(self):
        # reset all the modes if any are existing
        self.reset_modes()
        # reset all the data if any are existing
        self.reset_all_data()

        #update the operation mode label
        self.current_mode = "Load Image"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

        # Open a file dialog to select an image file
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self.ui_page, "Open Image File", "", "JPG Files (*.jpg); PNG Files (*.png); All Files (*)", options=options)

        if filename:
            # Load the image
            self.base_image = cv2.imread(filename, cv2.IMREAD_COLOR) # Load as grayscale for edge detection
            # Convert BGR to RGB format
            self.base_image = cv2.cvtColor(self.base_image, cv2.COLOR_BGR2RGB)

            # Create a plane with the same aspect ratio as the image
            image_shape = self.base_image.shape

            self.image_plane = pv.Plane(
                i_size=image_shape[1],  # Width of the plane
                j_size=image_shape[0],  # Height of the plane
                direction=(0, 0, 1)     # Plane facing up in the Z direction
            )

            #Apply the texture to the plane
            self.texture = pv.numpy_to_texture(self.base_image)  # Convert to RGB for display
            self.ui_page.plotter.load_image_to_canvas(self.image_plane, self.texture)
            self.ui_page.plotter.set_top_view()

        #update the operation mode label
        self.current_mode = "Default"
        self.ui_page.plotter.set_operation_mode(self.current_mode)
    
    def get_output_file_name(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self.ui_page, "Save Edited Mesh", "", "JSON Files (*.json);;All Files (*)", options=options)
        return filename
    
    # ------------------------------------------- MOUSE CONTROLS ----------------------------------------------------------------------------
    def on_left_button_press(self, obj, event):
        if self.calibrate_dimensions_mode:
            click_position = self.ui_page.plotter.iren.get_event_position()
            #get picked point
            click_position = self.get_point_on_plane(click_position)
            cross_size = (self.image_plane.bounds[1] - self.image_plane.bounds[0]) / 50  # Use the width of the image plane to determine the cross size
            if self.calibration_start_point is None:
                # First point selection
                self.calibration_start_point = click_position
                self.draw_cross(self.calibration_start_point, cross_size)
                self.calibration_line_actor = self.ui_page.plotter.add_lines(np.array([self.calibration_start_point, self.calibration_start_point]), color='red')
            else:
                # Second point selection
                self.calibration_end_point = click_position
                self.draw_cross(self.calibration_end_point, cross_size)
                # Remove the old line and add the new one connecting start and end points
                self.ui_page.plotter.remove_actor(self.calibration_line_actor)
                self.calibration_line_actor = self.ui_page.plotter.add_lines(np.array([self.calibration_start_point, self.calibration_end_point]), color='red')
            
                # Prompt user for real-world dimension
                length = np.linalg.norm(np.array(self.calibration_end_point) - np.array(self.calibration_start_point))
                self.prompt_for_dimensions(length)

                # Disable the calibration mode after the second point is selected
                self.disable_calibration_mode()

            # Simulate a mouse button release event to stop interaction modes like rotation or panning
            mouse_release_event = QMouseEvent(QEvent.MouseButtonRelease, QCursor.pos(), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            self.ui_page.plotter.interactor.mouseReleaseEvent(mouse_release_event)
            self.ui_page.plotter.set_top_view()    # Reset the camera position to fit the mesh in the view
        
        elif self.is_region_drawing_mode:
            # Simulate a mouse button release event to stop interaction modes like rotation or panning
            mouse_release_event = QMouseEvent(QEvent.MouseButtonRelease, QCursor.pos(), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            self.ui_page.plotter.interactor.mouseReleaseEvent(mouse_release_event)

            # Start drawing the region after the first click of the mouse
            self.is_drawing = True    # Start drawing the region after the first click of the mouse
            self.drawing_points = []  # Reset the points list
        
        elif self.manual_routing_mode:
            click_position = self.ui_page.plotter.iren.get_event_position()
            #get picked point
            click_position = self.get_point_on_plane(click_position)
            #check the status of the clicked point whether it is a connector or an electrode or none
            status, point = self.check_routing_point_status(click_position)

            if not self.manual_routing_points:#path is not started yet
                if status == 'none':
                    self.ui_page.show_warning("Invalid Starting Point!\nPlease start the routing from an electrode or a connector")
                else:
                    self.manual_routing_start_type = status  #set the starting point type as connector or electrode
                    self.manual_routing_points.append(point) #add the center point of the conn of elec to the routing points
                    self.manual_routing_points.append([point[0]+0.05,point[1]+0.05,0]) #add delta for ribbon visualization stability
            else:
                # check and add subsequent points to the path
                if self.manual_routing_start_type == 'connector':
                    if status == 'connector':
                        self.ui_page.show_warning("Invalid Point!\nPlease finish the routing on a electrode")
                    elif status == 'electrode':
                        self.manual_routing_points.append(point) # add the center point of the electrode to the routing points
                        # add the routing points to the routing paths
                        xy_cords = [tuple(map(float, point[:2])) for point in self.manual_routing_points]
                        self.routing_paths.append(xy_cords)

                        #disable the manual routing mode - this will clear manual routing points
                        self.disable_manual_routing_mode()
                        self.update_display_content()
                    else:
                        self.manual_routing_points.append(click_position)
                
                elif self.manual_routing_start_type == 'electrode':
                    if status == 'electrode':
                        self.ui_page.show_warning("Invalid Point!\nPlease finish the routing on a connector")
                    elif status == 'connector':
                        self.manual_routing_points.append(point) # add the center point of the connector to the routing points
                        # add the routing points to the routing paths
                        xy_cords = [tuple(map(float, point[:2])) for point in self.manual_routing_points]
                        self.routing_paths.append(xy_cords)

                        #disable the manual routing mode - this will clear manual routing points
                        self.disable_manual_routing_mode()
                        self.update_display_content()
                    else:
                        self.manual_routing_points.append(click_position)
                
            # Simulate a mouse button release event to stop interaction modes like rotation or panning
            mouse_release_event = QMouseEvent(QEvent.MouseButtonRelease, QCursor.pos(), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            self.ui_page.plotter.interactor.mouseReleaseEvent(mouse_release_event)

        #Continue with the default interaction behavior
        # self.ui_page.plotter.iren.get_interactor_style().OnLeftButtonDown()

    def on_mouse_move(self, obj, event):
        if self.calibrate_dimensions_mode:
            if self.calibration_start_point is not None and self.calibration_line_actor is not None:
                cursor_location = self.ui_page.plotter.iren.get_event_position()

                # Convert click position to 3D point on the plane
                current_point = self.get_point_on_plane(cursor_location)

                # Remove the old line and add the new one dynamically connecting start point to current cursor location
                self.ui_page.plotter.remove_actor(self.calibration_line_actor)
                self.calibration_line_actor = self.ui_page.plotter.add_lines(np.array([self.calibration_start_point, current_point]), color='red')

        if self.is_region_drawing_mode and self.is_drawing:
            cursor_location = self.ui_page.plotter.iren.get_event_position()
            current_point = self.get_point_on_plane(cursor_location)
            if current_point is not None:
                self.drawing_points.append(current_point)
                self.ui_page.plotter.add_points(current_point, color='red', point_size=5)
        
        if self.manual_routing_mode and self.manual_routing_points:
            cursor_location = self.ui_page.plotter.iren.get_event_position()
            current_point = self.get_point_on_plane(cursor_location)
            current_point = [current_point[0], current_point[1], 0] #replace the z coordinate with 0
            if current_point is not None:
                if self.manual_routing_actor is not None: #remove the previous routing path
                    self.ui_page.plotter.remove_actor(self.manual_routing_actor)        
                #temporily take the routed points and the current point and draw the routing path
                routing_path = pv.PolyData(np.vstack([self.manual_routing_points, current_point]))
                
                routing_path.lines = np.hstack([[len(self.manual_routing_points) + 1], np.arange(len(self.manual_routing_points) + 1)])
                routing_path['distance'] = range(len(self.manual_routing_points) + 1)
                routing_path = routing_path.ribbon(width=self.track_width/2)

                self.manual_routing_actor = self.ui_page.plotter.add_mesh(routing_path, color= 'black')
        #Continue with the default interaction behavior
        # self.ui_page.plotter.iren.get_interactor_style().OnMouseMove()

    def on_left_button_release(self, obj, event):
        if self.is_region_drawing_mode and self.is_drawing:
            self.proccess_drawn_region()
            # Finish the drawing operations this should be done after processing of region since it uses some conditions
            self.drawing_points = []
            self.is_region_drawing_mode = False
            self.is_drawing = False

            #if we are in the eraser mode, we should maintain the region drawing mode
            if self.eraser_mode:
                self.is_region_drawing_mode = True
                self.is_drawing = False

            if self.adjust_elements_region_drawing_mode:
                self.adjust_elements_region_drawing_mode = False
                if len(self.original_electrode_points_to_adjust) > 0:
                    self.elements_available_to_adjust = True
                    self.visualise_adjusted_elements()
            
        #Continue with the default interaction behavior
        # self.ui_page.plotter.iren.get_interactor_style().OnLeftButtonUp()

    def get_point_on_plane(self, click_position):
        # Use vtkCellPicker to convert the 2D click position to 3D world coordinates
        picker = vtkCellPicker()
        picker.SetTolerance(0.001)  # Small tolerance for precision picking
        picker.Pick(click_position[0], click_position[1], 0, self.ui_page.plotter.renderer)

        #get picked point
        click_position = picker.GetPickPosition()
        return np.array([click_position[0], click_position[1], click_position[2]], dtype=np.float32)  # Convert to numpy array for easier manipulation
    
    # -------------------------------------------    UTILITIES      -------------------------------------------------------------------------    
    def create_pv_circle(self, center, radius, resolution=20):
        """
        Create a 2D circle (disk) at the given center with the specified radius.

        :param center: The (x, y) coordinates of the center of the circle.
        :param radius: The radius of the circle.
        :param resolution: The number of points used to represent the circle.
        :return: A PyVista PolyData object representing the circle.
        """
        theta = np.linspace(0, 2 * np.pi, resolution)
        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)
        z = np.full_like(x, 0)  # Zero Z coordinate for 2D circle

        # Create the points for the circle
        points = np.vstack((x, y, z)).T
        # Create a polygon that represents the circle
        faces = np.hstack([[resolution], np.arange(resolution)])
        # Create the PolyData object
        circle = pv.PolyData(points, faces)
        return circle
    
    def smooth_edge_points(self, points, window_length=5, polyorder=2):
        """
        Smooth the edge points using a Savitzky-Golay filter.
        
        :param points: numpy array of shape (n, 2), where n is the number of points
        :param window_length: The length of the filter window (must be an odd number)
        :param polyorder: The order of the polynomial used to fit the samples
        :return: Smoothed numpy array of points
        """
        if len(points) < window_length:
            window_length = len(points) - (len(points) % 2 == 0)  # Ensure odd window length

        x_smooth = savgol_filter(points[:, 0], window_length, polyorder)
        y_smooth = savgol_filter(points[:, 1], window_length, polyorder)
        
        return np.vstack([x_smooth, y_smooth]).T

    def update_display_content(self):
        self.ui_page.plotter.save_camera_view()
        #update the display with new content
        if self.image_plane:
            if self.show_image:
                self.ui_page.plotter.load_image_to_canvas(self.image_plane, self.texture) #this will clear and add the image to the canvas
            else:
                self.ui_page.plotter.load_image_to_canvas(self.image_plane, None) #this will clear the image from the canvas

        # Add the populated electrode points to the plotter
        if self.populated_electrode_points:
            for point in self.populated_electrode_points:
                circle = self.create_pv_circle(point, self.electrode_radius)
                self.ui_page.plotter.add_mesh(circle, color='blue', show_edges=False)
            
        
        # Add the captured contours
        if len(self.extracted_edge_contour_points) > 0:
            #add code to display the drawn contours of the outer image edge
            points = np.hstack([self.extracted_edge_contour_points, np.zeros((len(self.extracted_edge_contour_points), 1))])  # Add Z coordinate
            # Create a PolyData object to visualize
            pv_contour = pv.PolyData(points)
            pv_contour.lines = np.hstack([[len(points)], np.arange(len(points))])
            # Add the contour shape to the plotter
            self.ui_page.plotter.add_mesh(pv_contour, color='blue', line_width=2)

        # Add the connector segments
        if self.connector_segments:
            for pads_group in self.connector_polygons_data:
                for pad in pads_group:
                    boundary = pad.exterior.coords
                    num_points = len(boundary)
                    boundary = np.hstack([boundary, np.zeros((num_points, 1))])  # Add Z coordinate
                    # Create the faces for the polygon (just one face)
                    faces = np.hstack([[num_points], np.arange(num_points)])
                    # Create a PolyData object in PyVista
                    polydata = pv.PolyData(boundary, faces)

                    # self.ui_page.plotter.add_mesh(pads_mesh, color='green', show_edges=True)
                    self.ui_page.plotter.add_mesh(polydata, color='green', show_edges=True, line_width=2)
        
        # Add the routing traes
        if self.routing_paths:
            for routing_path in self.routing_paths:
                line_path = np.hstack([routing_path, np.zeros((len(routing_path), 1))])  # Add Z coordinate
                line_path = pv.PolyData(line_path) # Create a PolyData object for the selected points

                line_path.lines = np.hstack([[len(routing_path)], np.arange(len(routing_path))])
                line_path['distance'] = range(len(routing_path))
                line_path = line_path.ribbon(width=self.track_width/2)
                self.ui_page.plotter.add_mesh(line_path, color= 'black')
        
        #update the mode label
        self.ui_page.plotter.set_operation_mode(self.current_mode)

        self.ui_page.plotter.restore_camera_view()
    
    # ------------------------------------------------------- ERASER MODE   ------------------------------------------------------------------  
    def toggle_eraser_mode(self):
        #reset all the modes if any are existing
        temp_eraser_mode = self.eraser_mode
        self.reset_modes()  # Reset all modes before toggling eraser mode
        # If the eraser mode was already active, toggle it off
        self.eraser_mode = not temp_eraser_mode

        #enable the region drawing mode to place a curve along the trace
        self.is_region_drawing_mode = True
        self.is_drawing = False

        if self.eraser_mode:
            # Change cursor to indicate eraser mode (if possible with your UI framework)
            self.ui_page.plotter.setCursor(Qt.CrossCursor)  # Simplified cursor change; adjust as needed
            #update the operation mode label
            self.current_mode = "Eraser"
            self.ui_page.plotter.set_operation_mode(self.current_mode)
        else:
            self.ui_page.plotter.setCursor(Qt.ArrowCursor)
            #update the operation mode label
            self.current_mode = "Default"
            self.ui_page.plotter.set_operation_mode(self.current_mode)
        

    def erase_nearby_elements(self, eraser_center, eraser_tolerance = 1):
        # Erase nearby electrodes
        new_stored_points = []
        for point in self.populated_electrode_points:
            distance = np.linalg.norm(point - eraser_center[:2])
            if distance > eraser_tolerance: #no need to compare the z coordinate
                new_stored_points.append(point)
        self.populated_electrode_points = new_stored_points

        # Erase nearby connector footprints
        for pads_group_index in range(len(self.connector_polygons_data)):
            pads_group = self.connector_polygons_data[pads_group_index]
            for pad in pads_group:
                try: # sometimes distance calculation throws an error
                    distance = pad.distance(Point(eraser_center[:2]))
                    if distance < eraser_tolerance:
                        # Remove the whole group of pads
                        self.connector_polygons_data.pop(pads_group_index)
                        self.connector_pads_data.pop(pads_group_index)
                        self.connector_segments.pop(pads_group_index) #remove the connector segment as well
                        break
                except:
                    pass
        # Erase nearby routing traces
        new_routing_paths = []
        for routing_path in self.routing_paths:
            path_line = LineString(routing_path)
            try: # sometimes distance calculation throws an error
                if path_line.distance(Point(eraser_center[:2])) > eraser_tolerance:
                    new_routing_paths.append(routing_path)
            except:
                pass
        self.routing_paths = new_routing_paths

    # ------------------------------------------- DIMENSION CALIBRATION MODE -----------------------------------------------------------------
    def enable_dimensions_calibrate_mode(self):
        if self.base_image is None:
            self.ui_page.show_warning("Please load an image before calibrating dimensions")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        self.ui_page.plotter.setCursor(Qt.CrossCursor)  # Change cursor to crosshair
        self.calibrate_dimensions_mode = True
        self.calibration_start_point = None
        self.calibration_end_point = None
        self.calibration_line_actor = None
        self.cross_actors = []
        #update the operation mode label
        self.current_mode = "Dimension Calibration"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

    def draw_cross(self, point, size):
        # Draw a cross at the specified point
        x, y, z = point
        cross_lines = [
            np.array([[x - size, y, z], [x + size, y, z]]),
            np.array([[x, y - size, z], [x, y + size, z]]),
        ]
        for line in cross_lines:
            actor = self.ui_page.plotter.add_lines(line, color='black', width=4)
            self.cross_actors.append(actor)
    
    def prompt_for_dimensions(self, length):
        dimension, ok = QInputDialog.getDouble(self.ui_page, "Input Real Dimension", f"Line length in image: {length:.2f}\nEnter real-world length:")
        if ok:
            self.scale_factor = dimension / length
            # Apply scaling factor or other logic as needed
            self.calibrate_image_dimensions()

    def calibrate_image_dimensions(self):
        # Scale the image plane to real-world dimensions
        self.image_plane.points *= self.scale_factor
        self.extracted_edge_contour_points = []
        self.update_display_content()

        self.ui_page.plotter.set_top_view()

    def disable_calibration_mode(self):
        self.calibrate_dimensions_mode = False
        self.calibration_start_point = None
        self.calibration_end_point = None
        # Remove the line and crosses
        if self.calibration_line_actor:
            self.ui_page.plotter.remove_actor(self.calibration_line_actor)
            self.calibration_line_actor = None
        for actor in self.cross_actors:
            self.ui_page.plotter.remove_actor(actor)
        self.cross_actors.clear()
        self.ui_page.plotter.setCursor(Qt.ArrowCursor)  # Reset cursor to defaults
        #update the operation mode label
        self.current_mode = "Default"
        self.ui_page.plotter.set_operation_mode(self.current_mode)
    # -------------------------------------------       IMAGE HANDLING      -----------------------------------------------------------------
    def enable_image_edge_draw_mode(self):
        self.image_edge_drawing_mode = True
        self.is_region_drawing_mode = True # Enable region drawing mode as well
        self.is_drawing = False
        self.drawn_contour_points = []  # Reset the drawn contour points
        self.update_display_content() # Update the display will remove all the previous drawn contours since the points are reset
    
    def enable_image_view(self):
        if self.base_image is None:
            self.ui_page.show_warning("Please load an image before viewing")
        #reset all the modes if any are existing
        self.reset_modes()

        self.show_image = True
        self.update_display_content()
    
    def disable_image_view(self):
        if self.base_image is None:
            self.ui_page.show_warning("Please load an image before viewing")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        self.show_image = False
        self.update_display_content()
    
    def extract_edges(self):
        if self.base_image is None:
            self.ui_page.show_warning("Please load an image before extracting edges")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        # Convert the color image to grayscale for edge detection
        gray_image = cv2.cvtColor(self.base_image, cv2.COLOR_RGB2GRAY)
        # Detect edges using Canny edge detection
        low_threshold = 100  # Lower threshold for more sensitivity
        high_threshold = 200  # Upper threshold for more strong edges
        tolerance = 1  # Tolerance for contour simplification
        edges = cv2.Canny(gray_image, low_threshold, high_threshold)

        # Find contours from the edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Simplify contours based on the specified tolerance
        simplified_contours = [cv2.approxPolyDP(cnt, tolerance, True) for cnt in contours]

        if simplified_contours:
            # Assuming the largest contour is the outermost edge
            largest_contour = max(simplified_contours, key=cv2.contourArea)
            # Ensure the contour is closed
            if not np.array_equal(largest_contour[0], largest_contour[-1]):
                largest_contour = np.append(largest_contour, [largest_contour[0]], axis=0)
            # Convert the contour on the image plane
            height, width = self.base_image.shape[:2]
            points = np.array([
                [
                    pt[0][0]- width / 2,  # X coordinate adjusted to the plane's origin
                    height / 2 - pt[0][1],  # Y coordinate adjusted and inverted
                    0  # Z coordinate stays at 0, flat on the image plane
                ] for pt in largest_contour
            ], dtype=np.float32)
            
            # Apply the scaling factor to the contour points
            bounds = self.image_plane.bounds
            width = bounds[1] - bounds[0]
            scale = width/ self.base_image.shape[1] # Always scale based on the current width of the image plane and the original image width, because contour is based on the original image
            points *= scale

            # Getting the contour on the plane for shapely operations
            self.extracted_edge_contour_points = points[:, :2] # Get only the X and Y coordinates for shapely contour
            self.update_display_content()

        #update the operation mode label
        self.current_mode = "Default"
        self.ui_page.plotter.set_operation_mode(self.current_mode)
    # ------------------------------------------------- REGION SELECTION  ---------------------------------------------------------------------
    def enable_electrode_region_drawing(self):
        if len(self.extracted_edge_contour_points) == 0:
            self.ui_page.show_warning("Please extract the image edge first before drawing the electrode regions")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        self.electrode_region_drawing_mode = True
        self.is_region_drawing_mode = True
        self.is_drawing = False
        #update the operation mode label
        self.current_mode = "Drawing Electrode Region"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

    def generate_electrode_points(self, contour_polygon, distance):
        # Calculate the bounding box of the contour
        min_x, min_y, max_x, max_y = contour_polygon.bounds

        # Generate a grid of points within the bounding box
        x_coords = np.arange(min_x, max_x, distance)
        y_coords = np.arange(min_y, max_y, distance)
        grid_points = np.array(np.meshgrid(x_coords, y_coords)).T.reshape(-1, 2)

        if len(self.extracted_edge_contour_points) > 0:
            # Convert the drawn contour points to a shapely polygon
            main_contour_polygon = Polygon(self.extracted_edge_contour_points)
            #offset the polygon to prevent electrodes on the edges
            main_contour_polygon = main_contour_polygon.buffer(-self.electrode_radius*2)

            # Filter points inside the main contour
            points_inside = [Point(pt).within(main_contour_polygon) and Point(pt).within(contour_polygon) for pt in grid_points]
            selected_points = grid_points[points_inside]
        else:
            # Raise a warning if the main contour is not drawn
            self.ui_page.show_warning("Please draw the main contour before generating electrodes")
            selected_points = [] #return empty list if the main contour is not drawn
        return selected_points

    def proccess_drawn_region(self):
        if len(self.drawing_points) > 2:
            # We do not need to close the loop for the connectors
            if self.connector_region_drawing_mode:
                # Add the selected points to the plotter and update the display accordingly
                points = np.array(self.drawing_points, dtype=np.float32)
                self.connector_segments.append(points[:, :2])

                paths_as_linestrings = [LineString(segment) for segment in self.connector_segments]
                # Now you use these LineString objects in the function that generates the pads
                self.connector_pads_data, self.connector_polygons_data = self.place_connector_pads_on_lines(paths_as_linestrings)

                self.connector_region_drawing_mode = False #Connectors are updated when diplay is updated
                #update the operation mode label
                self.current_mode = "Default"


            if self.eraser_mode:
                # Erase nearby elements
                for point in self.drawing_points:
                    self.erase_nearby_elements(point)

            # Close the loop by connecting the last point to the first point
            self.drawing_points.append(self.drawing_points[0])
            # numpy array of the points
            points = np.array(self.drawing_points, dtype=np.float32)

            if self.image_edge_drawing_mode:
                # Smooth the edge points using a Savitzky-Golay filter
                points = self.smooth_edge_points(points[:, :2])
                # Ensure the polygon is closed
                if not np.array_equal(points[0], points[-1]):
                    points = np.vstack([points, points[0]])

                # Get the region as a shapely polygon for further processing
                self.drawn_contour_points.extend(points)
                self.image_edge_drawing_mode = False
                #update the operation mode label
                self.current_mode = "Default"

            if self.electrode_region_drawing_mode:
                # Get the region as a shapely polygon for further processing
                region_polygon = Polygon(points[:, :2])

                electrode_points = self.generate_electrode_points(region_polygon, distance=self.electrode_gap)
                # Should check if the points are within the main image edge region
                self.populated_electrode_points.extend(electrode_points)
                self.electrode_region_drawing_mode = False
                #update the operation mode label
                self.current_mode = "Default"

            if self.adjust_elements_region_drawing_mode:
                # Get the region as a shapely polygon for further processing
                region_polygon = Polygon(points[:, :2])
                # Get the points to adjust
                self.original_electrode_points_to_adjust.extend(self.get_adjusting_electrodes(region_polygon))
                self.adjusted_electrode_points = self.original_electrode_points_to_adjust.copy()

            # Add the selected points to the plotter and update the display accordingly
            self.update_display_content()

    # ------------------------------------------------- CONNECTOR PLACEMENT  -----------------------------------------------------------------
    def enable_connector_region_drawing(self):
        if len(self.extracted_edge_contour_points) == 0:
            self.ui_page.show_warning("Please extract the image edge first before drawing the connector regions")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        self.connector_region_drawing_mode = True
        self.is_region_drawing_mode = True
        self.is_drawing = False
        #update the operation mode label
        self.current_mode = "Drawing Connector Line"
        self.ui_page.plotter.set_operation_mode(self.current_mode)
    
    def generate_connector_footprint(self, start_end_pad_width, start_end_pad_height, middle_pad_width, middle_pad_height, num_middle_pads, middle_pad_spacing, holding_start_spacing, y_offset):
        """
        Generates a footprint with specific start and end pads of one size, and multiple middle pads of another size.

        Returns:
        - a list of information [center.x, center.y, width, height, polygon] for each pad
        """
        #dimensions in mm
        # middle_pad_spacing - spacing between the middle pads edge to edge
        # holding_start_spacing - spacing between the holding pad end and the starting edge of the middle pad
        # y_offset - offset of the middle pads from the origin.bottom of the holding pad

        pad_data = []
        
        footprint_width = 2 * start_end_pad_width + num_middle_pads * middle_pad_width + (num_middle_pads - 1) * middle_pad_spacing + 2 * holding_start_spacing
        footprint_height = max(y_offset + middle_pad_height, start_end_pad_height)

        # Create the first pad
        first_pad = Polygon([(0, 0),
                            (start_end_pad_width, 0),
                            (start_end_pad_width, start_end_pad_height),
                            (0, start_end_pad_height)])
        
        pad_placed = translate(
                first_pad,
                -footprint_width/2,
                -footprint_height/2
            )
        pad_info = [pad_placed.centroid.x, pad_placed.centroid.y , start_end_pad_width, start_end_pad_height, pad_placed] #x, y, width, height
        pad_data.append(pad_info)

        # Calculate the starting x position for the middle pads
        x_position = start_end_pad_width + holding_start_spacing
        y_position = y_offset#do the offset for y properly
        
        # Create middle pads
        for _ in range(num_middle_pads):
            middle_pad = Polygon([
                (x_position, y_position),
                (x_position + middle_pad_width, y_position),
                (x_position + middle_pad_width, middle_pad_height + y_position),
                (x_position, middle_pad_height + y_position)
            ])

            pad_placed = translate(
                middle_pad,
                -footprint_width/2,
                -footprint_height/2
            )

            pad_info = [pad_placed.centroid.x, pad_placed.centroid.y , middle_pad_width, middle_pad_height, pad_placed] #x, y, width, height
            pad_data.append(pad_info)

            x_position += middle_pad_width + middle_pad_spacing  # Move the x position for the next pad
        
        x_position -= middle_pad_spacing  # Adjust the x position for the last pad
        x_position += holding_start_spacing  # Add the spacing for the last pad
        # y_position = 0  # Reset the y position for the last pad
        
        # Create the last pad
        last_pad = Polygon([
            (x_position, 0),
            (x_position + start_end_pad_width, 0),
            (x_position + start_end_pad_width, start_end_pad_height),
            (x_position, start_end_pad_height)
        ])

        pad_placed = translate(
                last_pad,
                -footprint_width/2,
                -footprint_height/2
            )
        pad_info = [pad_placed.centroid.x, pad_placed.centroid.y , start_end_pad_width, start_end_pad_height, pad_placed] #x, y, width, height
        pad_data.append(pad_info)
        return pad_data
    
    def place_connector_pads_on_lines(self, base_lines):
        '''return two lists
        a list: a list of information [ [center.x, center.y, width, height, angle] for each pad]
        polygon data: a [[list of polygons] for each pad]'''
        pad_info = []
        polygon_data = []
        
        for segment in base_lines:
            total_length = segment.length
            s_param = total_length/2
            point = segment.interpolate(s_param)
        
            next_point = segment.interpolate(s_param + 1)

            dx = next_point.x - point.x
            dy = next_point.y - point.y
            angle = np.degrees(np.arctan2(dy, dx))

            #Creating a connector
            base_connector_pads_data = self.generate_connector_footprint(start_end_pad_width=self.holding_pad_width,
                                                                         start_end_pad_height=self.holding_pad_height,
                                                                         middle_pad_width=self.pad_width,
                                                                         middle_pad_height=self.pad_height,
                                                                         num_middle_pads=self.num_pads,
                                                                         middle_pad_spacing=self.pad_spacing,
                                                                         holding_start_spacing=1.2,
                                                                         y_offset=3.7)
            
            # Creating and positioning the pad with width oriented towards the contour
            temp_pad_info = []
            temp_polygon_data = []
            for pad_data in base_connector_pads_data:
                connector_polygon = pad_data[4] #last element has the polygon info
                connector_rotated = rotate(connector_polygon, angle, origin=(0, 0)) #1st adn 2nd has the centroid data
                connector_placed = translate(
                    connector_rotated,
                    point.x,
                    point.y
                )

                temp_pad_info.append([connector_rotated.centroid.x + point.x, connector_rotated.centroid.y + point.y , pad_data[2], pad_data[3], angle])
                temp_polygon_data.append(connector_placed)
            
            #now we have a list of pads for each connector and list of polygons of pads for each connector
            pad_info.append(temp_pad_info)
            polygon_data.append(temp_polygon_data)

        return pad_info, polygon_data
    
    # ----------------------------------------------------- ELEMENT ADJUSTMENT -----------------------------------------------------------------
    def show_adjust_dialog(self):
        #reset all the modes if any are existing
        self.reset_modes()
        
        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        dialog_width  = self.ui_page.adjust_dialog.width()  # x position
        dialog_height = self.ui_page.adjust_dialog.height() # y position

        desired_x = screen_size.width() - dialog_width - 1000  # 100px in from the right edge
        desired_y = 300  # 50px from the top

        # Move the dialog to (desired_x, desired_y) in *global* screen coordinates:
        self.ui_page.adjust_dialog.move(desired_x, desired_y)

        # Show the adjust dialog
        # self.ui_page,adjust_dialog.exec_() # or dialog.show() if you want non-modal
        self.ui_page.adjust_dialog.show()

    def enable_element_adjustment(self):
        # if len(self.populated_electrode_points) == 0 and len(self.connector_polygons_data) == 0:
        #     self.ui_page.show_warning("Please populate the electrodes and connectors before adjusting elements")
        #     return
        if len(self.populated_electrode_points) == 0:
            self.ui_page.show_warning("Please populate the electrodes before adjusting elements")
            return
        #reset all the modes if any are existing
        self.reset_modes()
        self.adjust_elements_region_drawing_mode = True
        self.elements_available_to_adjust = False
        self.is_region_drawing_mode = True
        self.is_drawing = False
        # reset all the adjustment variables
        self.adjusted_electrode_points = []
        if self.current_mode != "Adjusting Electrodes":    #if we are not already in the adjusting mode
            self.original_electrode_points_to_adjust = []
        #else the original electrode points to adjust will be the same as the previous one
        self.adjusted_electrode_actors = []
        self.total_adjust_element_x = 0
        self.total_adjust_element_y = 0
        self.adjust_element_rotation = 0
        self.ui_page.adjust_dialog.angle_input.setText(str(self.adjust_element_rotation) + "°")
        #update the operation mode label
        self.current_mode = "Adjusting Electrodes"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

    def finalize_element_adjustment(self):
        # append the adjusted electrodes to the populated electrodes
        self.populated_electrode_points.extend(self.adjusted_electrode_points)
        self.adjusted_electrode_points = []
        self.original_electrode_points_to_adjust = []
        self.adjust_elements_region_drawing_mode = False
        self.elements_available_to_adjust = False
        self.adjusted_electrode_actors.clear()
        self.update_display_content()
        #update the operation mode label
        self.current_mode = "Default"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

    # Adjust the position of the selected element
    def adjust_up(self):
        if self.elements_available_to_adjust == False:
            self.ui_page.show_warning("Please select elements to adjust")
            return
        self.total_adjust_element_y += self.adjust_step_size
        self.transform_adjustable_electrodes()

    def adjust_down(self):
        if self.elements_available_to_adjust == False:
            self.ui_page.show_warning("Please select elements to adjust")
            return
        self.total_adjust_element_y -= self.adjust_step_size
        self.transform_adjustable_electrodes()

    def adjust_left(self):
        if self.elements_available_to_adjust == False:
            self.ui_page.show_warning("Please select elements to adjust")
            return
        self.total_adjust_element_x -= self.adjust_step_size
        self.transform_adjustable_electrodes()

    def adjust_right(self):
        if self.elements_available_to_adjust == False:
            self.ui_page.show_warning("Please select elements to adjust")
            return
        self.total_adjust_element_x += self.adjust_step_size
        self.transform_adjustable_electrodes()

    def reset_transform(self):
        if self.elements_available_to_adjust == False:
            self.ui_page.show_warning("Please select elements to adjust")
            return
        if self.ui_page.get_confirmation("Resetting Transform", "Are you sure you want reset the transformation?") == False:
            return  
        self.inverse_transform_adjustable_electrodes()
        self.total_adjust_element_x = 0
        self.total_adjust_element_y = 0
        self.adjust_element_rotation = 0
        self.ui_page.adjust_dialog.angle_input.setText(str(self.adjust_element_rotation) + "°")

    def get_adjusting_electrodes(self, contour_polygon):
        # Get the electrodes to adjust

        new_electrodes = []
        adjusting_electrodes = []
        for electrode in self.populated_electrode_points:
            if Point(electrode).within(contour_polygon):
                adjusting_electrodes.append(electrode)
            else:
                new_electrodes.append(electrode)
        self.populated_electrode_points = new_electrodes
        return adjusting_electrodes
    
    def transform_adjustable_electrodes(self):
        """
        Moves (translates) the selected points by (total_adjust_element_x, total_adjust_element_y),
        and rotates them about their centroid by self.adjust_element_rotation.
        """
        if not self.original_electrode_points_to_adjust:
            return
        
        # 1) Convert the points to a numpy array for easier manipulation
        arr = np.array(self.original_electrode_points_to_adjust, dtype=float)
        cx = arr[:,0].mean()
        cy = arr[:,1].mean()

        theta = math.radians(self.adjust_element_rotation)
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        # Shift by -centroid
        arr[:, 0] -= cx
        arr[:, 1] -= cy

        # Rotate
        x_temp = arr[:, 0].copy()
        y_temp = arr[:, 1].copy()

        arr[:, 0] = x_temp*cos_t - y_temp*sin_t
        arr[:, 1] = x_temp*sin_t + y_temp*cos_t

        # Shift back by centroid + global offset
        arr[:, 0] += (cx + self.total_adjust_element_x)
        arr[:, 1] += (cy + self.total_adjust_element_y)
        
        # 4) Store the updated points back to the list (if needed)
        self.adjusted_electrode_points = arr.tolist()

        self.visualise_adjusted_elements()
    
    def inverse_transform_adjustable_electrodes(self):
        """
        Moves (translates) the selected points by (-total_adjust_element_x, -total_adjust_element_y),
        and rotates them about their centroid by -self.adjust_element_rotation.
        """
        if not self.original_electrode_points_to_adjust:
            return
        
        # replace the adjusted electrodes with the original electrodes
        self.adjusted_electrode_points = self.original_electrode_points_to_adjust.copy()

        self.visualise_adjusted_elements()

    def visualise_adjusted_elements(self):
        # 1) remove all the old electrode actors
        for actor in self.adjusted_electrode_actors:
            self.ui_page.plotter.remove_actor(actor)
        self.adjusted_electrode_actors.clear() # Clear the list of actors

        # 2) save the camera view
        self.ui_page.plotter.save_camera_view()

        # 3) Add the transfomed electrode points to the plotter
        for point in self.adjusted_electrode_points:
            circle = self.create_pv_circle(point, self.electrode_radius)
            actor = self.ui_page.plotter.add_mesh(circle, color='red', show_edges=False)
            self.adjusted_electrode_actors.append(actor)
        self.ui_page.plotter.restore_camera_view()
    
    # -----------------------------------------------------   MANUAL ROUTING   ---------------------------------------------------------------------
    def enable_manual_routing_mode(self):
        if len(self.populated_electrode_points) == 0 or len(self.connector_polygons_data) == 0:
            self.ui_page.show_warning("Please place electrodes and connectors before starting manual routing")
            return
        #reset all the modes if any are existing
        self.reset_modes()

        self.ui_page.plotter.setCursor(Qt.CrossCursor)  # Change cursor to crosshair
        self.manual_routing_mode = True
        self.manual_routing_points = []
        self.manual_routing_actor = None
        self.manual_routing_start_type = None  # Type of the starting point (connector or electrode)
        #update the operation mode label
        self.current_mode = "Manual Routing"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

    def is_point_on_electrode(self, point):
        for electrode in self.populated_electrode_points:
            distance = np.linalg.norm(electrode - point[:2])
            if distance < self.electrode_radius:
                return [True, [electrode[0], electrode[1], 0]]
        return [False, None]
    
    def is_point_on_connector(self, point):
        for pad_group in self.connector_polygons_data:
            for pad in pad_group[1:-1]:  # Skip the first and last pads (ground pads)
                if pad.contains(Point(point[:2])):
                    return [True, [pad.centroid.x, pad.centroid.y, 0]]
        return [False, None]

    def check_routing_point_status(self, point):
        # Check if the point is on an electrode or a connector
        is_electrode, elec_center = self.is_point_on_electrode(point)
        is_connector, conn_center = self.is_point_on_connector(point)
        if is_electrode:
            return 'electrode', elec_center
        elif is_connector:
            return 'connector', conn_center
        return 'none', None

    def disable_manual_routing_mode(self):
        self.manual_routing_mode = False
        self.manual_routing_points = []
        self.manual_routing_start_type = None
        if self.manual_routing_actor is not None:
            self.ui_page.plotter.remove_actor(self.manual_routing_actor)
            self.manual_routing_actor = None
        self.ui_page.plotter.setCursor(Qt.ArrowCursor)
        #update the operation mode label
        self.current_mode = "Default"
        self.ui_page.plotter.set_operation_mode(self.current_mode)
    
    # ------------------------------------------------------ AUTOMATIC ROUTING ------------------------------------------------------------------
    def generate_conductive_traces(self):  
        if len(self.populated_electrode_points) == 0 or len(self.connector_polygons_data) == 0:
            self.ui_page.show_warning("Please populate the electrodes and connectors before manual routing")
            return
        #reset all the modes if any are existing
        self.reset_modes()
        #update the operation mode label
        self.current_mode = "Automatic Routing"
        self.ui_page.plotter.set_operation_mode(self.current_mode)

        def sort_info_left_to_right(points):
            """
            Sorts a list of points (tuples) based on their x-coordinate.
            If two points have the same x-coordinate, it further sorts by y-coordinate.
            """
            return sorted(points, key=lambda point: [point[0], point[1]])
        
        def sort_info_right_to_left(points):
            """
            Sorts a list of points (tuples) based on their x-coordinate in descending order.
            If two points have the same x-coordinate, it further sorts by y-coordinate.
            """
            return sorted(points, key=lambda point: [point[0], point[1]])[::-1]
        
        def calculate_angle(start_point, end_point):
            """
            Calculate the angle (in radians) of the line from start_point to end_point relative to the positive x-axis.
            """
            dx = end_point[0] - start_point[0]
            dy = end_point[1] - start_point[1]
            angle = math.atan2(dy, dx)
            return angle

        def find_leftmost_endpoint(start_point, end_points):
            """
            Given a start point and a set of end points, find the end point that forms the smallest positive angle
            when the line from start to end point is rotated anti-clockwise.
            """
            leftmost_point = None
            min_angle = float('inf')

            for end_point in end_points:
                angle = calculate_angle(start_point, end_point)
                
                # We want the smallest positive angle
                if angle < min_angle:
                    min_angle = angle
                    leftmost_point = end_point

            return leftmost_point
        
        def check_unrouted_electrodes_connectors(electrode_centers, connector_centers):
            electrodes = []
            connectors = []
            if self.routing_paths:
                for electrode in electrode_centers:
                    for path in self.routing_paths:
                        start = path[0]
                        end = path[-1]
                        if np.linalg.norm(np.array(start) - np.array(electrode)) < 1e-3:
                            break
                        if np.linalg.norm(np.array(end) - np.array(electrode)) < 1e-3:
                            break
                    else: # If the loop completes without breaking, the electrode is not connected
                        electrodes.append(electrode)
                
                for connector in connector_centers:
                    for path in self.routing_paths:
                        start = path[0]
                        end = path[-1]
                        if np.linalg.norm(np.array(end) - np.array(connector)) < 1e-3:
                            break
                        if np.linalg.norm(np.array(start) - np.array(connector)) < 1e-3:
                            break
                    else: # If the loop completes without breaking, the connector is not connected
                        connectors.append(connector)
                return electrodes, connectors
            else:
                return electrode_centers, connector_centers
        
        # Show the progress dialog
        progress_dialog = self.ui_page.show_progress_window()
        #calculations for the progreee bar
        progress_dialog.setValue(15)  # Set the initial progress value
        QApplication.processEvents()  # Keep the GUI responsive

        if len(self.extracted_edge_contour_points) > 0:
            # Convert the drawn contour points to a shapely polygon
            drawn_contour_polygon = Polygon(self.extracted_edge_contour_points)

            # Get all the electrode points within the drawn contour
            electrode_points = self.populated_electrode_points.copy()

            # ---------------------------------------Handling pad information ------------
            self.ground_pad_info = []      #ground pads are the first and last pads in the connector pads data
            self.connector_pad_info = []   #middle pads in the connector pads data
            for connector_group_data in self.connector_pads_data:
                #append first and last to ground pad info
                self.ground_pad_info.append(connector_group_data[0])
                self.ground_pad_info.append(connector_group_data[-1])
                #append the middle pads to the connector pad info
                self.connector_pad_info.extend(connector_group_data[1:-1])

            #sort the connector pad info from left point to right point
            self.connector_pad_info = sort_info_left_to_right(self.connector_pad_info)
            # self.connector_pad_info = sort_info_right_to_left(self.connector_pad_info)
           
            connector_points = [[info[0], info[1]] for info in self.connector_pad_info if drawn_contour_polygon.contains(Point([info[0], info[1]]))]

            #creating the electrode and connector polygons to exclude when routing
            connector_polygons = []  #contains all the pads including the ground pads
            for poly_group in self.connector_polygons_data:
                for poly in poly_group:
                    connector_polygons.append(poly) 
            
            electrode_polygons = [Point(electrode).buffer(self.electrode_radius) for electrode in self.populated_electrode_points]

            # ---------------------------------------------------------------------------------------------
            #initialize the routing process
            two_d_router = TwoDRouter(drawn_contour_polygon, self.electrode_radius, self.track_width, self.routing_clearance)

            # check what connectors and electrodes are not connected
            unconnected_electrodes, unconnected_connectors = check_unrouted_electrodes_connectors(electrode_points, connector_points)

            # generate the routing paths
            if len(unconnected_connectors) > 0 and len(unconnected_electrodes) > 0:
                self.routing_paths = two_d_router.route_connection_paths(start_points=unconnected_connectors,
                                                                    end_points=unconnected_electrodes,
                                                                    connector_polygons=connector_polygons,
                                                                    electrode_polygons=electrode_polygons,
                                                                    existing_paths=self.routing_paths.copy(),
                                                                    step = self.track_width + self.routing_clearance)
                #Close the dialog box
                progress_dialog.setValue(100)  # Ensure the progress reaches 100%
                progress_dialog.close()  # Close the dialog when done

            else:
                self.ui_page.show_warning("Please make sure there are electrodes and connectors before routing the connections.")
            
            #update the operation mode label
            self.current_mode = "Default"
            self.ui_page.plotter.set_operation_mode(self.current_mode)
            #update the display
            self.update_display_content()
        else:
            self.ui_page.show_warning("No Edge Contour!\n Please draw the edge contour before routing the connections.")
    
    def generate_output_files(self):
        # Get the output file name
        try:
            file_name = self.get_output_file_name()                
            # add the code to dump the json files
            self.generate_json_data(file_name,
                                    self.extracted_edge_contour_points,
                                    self.populated_electrode_points,
                                    self.connector_pads_data,
                                    self.routing_paths)
        except Exception as e:
            pass
    
    def generate_json_data(self, file_name, pcb_outline, electrode_points, connector_data, routing_paths):
        vias = []
        tracks_f = []
        tracks_b = []
        tracks_in = []
        pads = []
        vias = []
        pins = []
        mounting_holes = []
        silk = []
        components = []
        edge_cuts = []
        # ------------------------------- SEPERATING GND PADS AND CONNECTOR PADS -------------------------------------------------------
        ground_pad_info = []      #ground pads are the first and last pads in the connector pads data
        connector_pad_info = []   #middle pads in the connector pads data
        for connector_group_data in connector_data:
            #append first and last to ground pad info
            ground_pad_info.append(connector_group_data[0])
            ground_pad_info.append(connector_group_data[-1])
            #append the middle pads to the connector pad info
            connector_pad_info.extend(connector_group_data[1:-1])

        # ------------------------------------------- ADDING COMPONENTS -------------------------------------------------------
        routed_electrodes = []
        routed_connectors = []

        # Append the tracks data and connected electrodes and connectors
        for i in range(len(routing_paths)):
            tracks_b.append({"net": f"E{i}", "pts":routing_paths[i]})
            # Add the connector
            coords = routing_paths[i][0]
            for connector in connector_pad_info:
                if np.linalg.norm(np.array(connector[:2]) - np.array(coords)) < 1e-3:
                    pads.append(
                        create_rectangular_pad((connector[0], connector[1]), connector[2], connector[3], "f", f"E{i}", angle = connector[4], drill_size = 0)
                    )
                    routed_connectors.append(connector[:2])
                    break
            # Add the electrode
            coords = routing_paths[i][-1]
            for electrode in electrode_points:
                if np.linalg.norm(np.array(electrode) - np.array(coords)) < 1e-3:
                    pads.append(
                        create_circular_pad((electrode[0], electrode[1]), self.electrode_radius*2, self.electrode_radius*2,  "f", f"E{i}", drill_size = 0.2)    
                    )
                    routed_electrodes.append(electrode)
                    break
        
        # Append the remaining electrodes
        for electrode in electrode_points:
            for added_electrode in routed_electrodes:
                if np.linalg.norm(np.array(electrode) - np.array(added_electrode)) < 1e-3:
                    break
            else:
                pads.append(
                    create_circular_pad((electrode[0], electrode[1]), self.electrode_radius*2, self.electrode_radius*2,  "f", f"UE", drill_size = 0.2)    
                )

        # Append the remaining connectors
        for connector in connector_pad_info:
            for added_connector in routed_connectors:
                if np.linalg.norm(np.array(connector[:2]) - np.array(added_connector)) < 1e-3:
                    break
            else:
                pads.append(
                    create_rectangular_pad((connector[0], connector[1]), connector[2], connector[3], "f", f"UC", angle = connector[4], drill_size = 0)
                )

        # Append GND Pads
        for i in range(len(ground_pad_info)):
            pads.append(
                create_rectangular_pad((ground_pad_info[i][0], ground_pad_info[i][1]), ground_pad_info[i][2], ground_pad_info[i][3], "f", "GND", angle = ground_pad_info[i][4], drill_size = 0) 
            )
        
        # Append the outline of the PCB
        pcb_outline = [tuple(map(float, point)) for point in pcb_outline]
        edge_cuts.append(pcb_outline)
        # ------------------------------------------------------------------------------------------------------------


        # dump out the json version
        json_result = dump_json(
            filename= file_name,
            track_width= self.track_width,
            pin_diam= 1.0,
            pin_drill= 0.65,
            via_diam = 0.2 + 0.4,
            via_drill = 0.2,
            vias=vias,
            pins=pins,
            pads=pads,
            silk=silk,
            tracks_f=tracks_f,
            tracks_in=tracks_in,
            tracks_b=tracks_b,
            mounting_holes=mounting_holes,
            edge_cuts=edge_cuts,
            components=components,
        )

        import json
        # Convert each tuple into a dictionary with "x" and "y" keys
        outline_formatted = [{"x": x, "y": y} for x, y in pcb_outline]
        electrodes_formatted = [{"x": x, "y": y} for x, y in electrode_points]
        mapping_function = [i for i in range(len(electrode_points))]

        # Create a dictionary structure to store both lists
        data = {
            "outline": outline_formatted,
            "electrodes": electrodes_formatted,
            "Mapping_func": mapping_function,
            "electrode_radius": self.electrode_radius
        }

        # Save to a JSON file
        with open(file_name.strip('.json')+'contour_and_electrodes.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)  # 'indent=4' makes the JSON more readable


# ------------------------------------------- PATH SEARCH ON MESH ------------------------------------------------------------------
class TwoDRouter:
    def __init__(self, contour_polygon, electrode_radius, track_width, routing_clearance):
        """
        Initialize the PointInMeshChecker with a given mesh.

        :param mesh: The input mesh (PyVista PolyData or UnstructuredGrid).
        """
        self.contour_polygon = contour_polygon.buffer(-(routing_clearance + track_width/2)) #offset to prevent traces reaching the edge
        self.electrode_radius = electrode_radius
        self.track_width = track_width
        self.routing_clearance = routing_clearance
        # Initialize the set of occupied points
        self.occupied_points = set()
        self.keep_out_polygons = []
        self.paths = []

    # Check if the given tuple is in the set within the tolerance
    def tuple_inside_tolerance(self, given_tuple, tuple_set, tolerance = 1e-3):
        for t in tuple_set:
            if all(abs(a - b) <= tolerance for a, b in zip(given_tuple, t)):
                return t
        return None
    
    def is_valid_point(self, point):
        # Check if the point is inside the contour and not occupied
        for polygon in self.keep_out_polygons:
            if polygon.contains(Point(point)):
                return False
            
        for path in self.paths:
            path_line = LineString(path)
            if path_line.distance(Point(point)) < self.track_width + self.routing_clearance:
                return False
            
        return self.contour_polygon.contains(Point(point)) and self.tuple_inside_tolerance(tuple(point), self.occupied_points) is None

    # ---------------------------------------------------------
    def snap_point_to_grid(self, point, step):
        """snaps the point to the closest grid point"""
        # Snap the point to the closest grid point
        x = round(point[0] / step) * step
        y = round(point[1] / step) * step
        
        # round_point = np.array([x, y], dtype=float)
        round_point = [x, y]
        return round_point

    def heuristic_euclidean(self, p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))
    
    def get_neighbors(self, point, step):
        directions = [
            np.array([dx, dy]) * step
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            if not (dx == 0 and dy == 0)
        ]

        neighbors = []
        for direction in directions:
            neighbor = np.array(point) + direction
            neighbor_mid_point = (np.array(point) + neighbor) / 2
            if self.is_valid_point(neighbor) and self.is_valid_point(neighbor_mid_point): # Check if the midpoint is also valid
                neighbors.append(tuple(neighbor))
        return neighbors

    def a_star(self, start, end, step, similarity_tolerance=1e-3):
        start = tuple(start)
        end = tuple(end)
        beta = 0#self.heuristic_euclidean(start, end)  # Penalty for moving right

        queue = [] 
        g_costs = {start: 0}                           # cost developed by traversing
        f_costs = {start: self.heuristic_euclidean(start, end)}  # cost based on the remaining distance+distance traversed
        previous_nodes = {start: None}
        heapq.heappush(queue, (f_costs[start], start))
        
        while queue:
            current_f_cost, current_point = heapq.heappop(queue)
            if np.linalg.norm(np.array(current_point) - np.array(end)) < similarity_tolerance:
                path = []
                while previous_nodes[current_point] is not None:
                    path.append(np.array(current_point))
                    current_point = previous_nodes[current_point]
                path.append(np.array(start))
                path.reverse()
                return path
    
            for neighbor in self.get_neighbors(current_point, step):
                # tentative_g_cost = g_costs[current_point] + 1 #np.linalg.norm(np.array(current_point) - np.array(neighbor))
                direction = np.array(neighbor) - np.array(current_point)
                move_cost = np.linalg.norm(direction)
                
                penalty = 0
                if direction[0] > 0:
                    penalty = 0
                elif direction[0] < 0:
                    penalty = beta    #penalize leftward moves
                    
                # penalty = beta if direction[0] > 0 else 0  # Penalize rightward moves
                tentative_g_cost = g_costs[current_point] + move_cost + penalty
                similar_point = self.tuple_inside_tolerance(neighbor, g_costs)
                if similar_point is None:
                    g_costs[neighbor] = tentative_g_cost
                    f_costs[neighbor] = tentative_g_cost + self.heuristic_euclidean(neighbor, end)
                    previous_nodes[neighbor] = current_point
                    heapq.heappush(queue, (f_costs[neighbor], neighbor))
                elif tentative_g_cost < g_costs[similar_point]:
                    g_costs[similar_point] = tentative_g_cost
                    f_costs[similar_point] = tentative_g_cost + self.heuristic_euclidean(similar_point, end)
                    previous_nodes[similar_point] = current_point
                    heapq.heappush(queue, (f_costs[similar_point], similar_point))
        return None

    def add_visited(self, current, neighbor):
        # Add current and neighbor to occupied
        self.occupied_points.add(tuple(current))
        self.occupied_points.add(tuple(neighbor))
        # If moving diagonally, add the midpoint
        if np.count_nonzero(current - neighbor) > 1:  # Check if diagonal
            midpoint = (current + neighbor) / 2
            self.occupied_points.add(tuple(midpoint))
    
    def route_connection_paths(self, start_points, end_points, connector_polygons, electrode_polygons, existing_paths, step):
        self.paths = existing_paths
        missed_ends = []
        original_end_points = end_points.copy()
        while start_points:
            if not end_points:
                # We can check the missed ends and also if there are any start points left and try routing them again
                return self.paths
            current_start = start_points.pop(0)
            current_end = end_points.pop(0)

            #-------------------------------------------------------- update the keep out polygons for each iteration --------------------------------
            self.keep_out_polygons = []
            #Appending the electrode polygons to the keep out polygons
            for polygon in electrode_polygons:
                if not polygon.contains(Point(current_end)):
                    self.keep_out_polygons.append(polygon.buffer(self.track_width/2 + self.routing_clearance))

            #Appending the connector polygons to keep out polygons
            for polygon in connector_polygons: #get only the connector polygon without the start point
                if not polygon.contains(Point(current_start)):
                    self.keep_out_polygons.append(polygon.buffer(self.track_width/2 + self.routing_clearance))
            # -----------------------------------------------------------------------------------------------------------------------------------------

            snapped_start = np.array(self.snap_point_to_grid(current_start, step))
            snapped_end = np.array(self.snap_point_to_grid(current_end, step))

            path_points = self.a_star(snapped_start, snapped_end, step)

            if path_points:
                print("Path found")
                # Add original start and end points to the path
                path_points.insert(0, current_start)
                path_points.append(current_end)

                # Add the path points to the occupied set
                for i in range(len(path_points) - 1):
                    self.add_visited(path_points[i], path_points[i + 1])

                # Remove the snapped points after they are added to the occupied set
                path_points.pop(1)
                path_points.pop(-2)
                # Convert path points to a format suitable for Polyline creation or storage
                path_points = [tuple(map(float, point)) for point in path_points]

                self.paths.append(path_points)
            else:
                print("No path found")
                missed_ends.append(current_end)
                start_points.insert(0, current_start)

        return self.paths


