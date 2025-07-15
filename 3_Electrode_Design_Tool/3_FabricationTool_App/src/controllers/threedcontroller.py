from PyQt5.QtWidgets import QFileDialog, QApplication, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt

import pyvista as pv
import numpy as np
import vtk
import heapq

import pyacvd
from pymeshfix import MeshFix

# from vtk import vtkIntersectionPolyDataFilter
from pyvista.core.filters import _get_output
from scipy.spatial import cKDTree

import json
class ThreeDController:
    def __init__(self, ui_page):
        self.ui_page = ui_page

        # Connect the UI buttons to their respective functions in 3D editor
        self.ui_page.load_mesh_button.clicked.connect(self.load_mesh)
        self.ui_page.simplify_slider.sliderReleased.connect(self.simplify_mesh)
        self.ui_page.select_electrode_faces_button.clicked.connect(self.enable_electrode_face_mode)
        self.ui_page.select_connector_faces_button.clicked.connect(self.enable_connector_face_mode)
        self.ui_page.finish_selection_button.clicked.connect(self.finish_face_selection)
        self.ui_page.export_mesh_button.clicked.connect(self.prepare_export_meshes)

        # Connect signals from UI for the laser cut editor-line edits
        self.ui_page.elec_diameter_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.elec_gap_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.conn_diameter_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.conn_gap_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.trace_diameter_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.trace_clearance_input.editingFinished.connect(lambda: self.update_parameters())
        self.ui_page.export_all_conductive_meshes_checkbox.stateChanged.connect(lambda: self.update_parameters())

        # Initialize variables for mesh handling
        self.mesh = None
        self.original_mesh = None

        # Initialize variables for electrode Handling
        self.select_electrode_faces_mode = False  # Track whether face selection mode is active
        self.selected_electrode_faces = set()
        self.selected_electrode_points = []
        self.electrode_radius = self.read_parameter(self.ui_page.elec_diameter_input)/2  # The radius of the electrodes
        self.target_electrode_gap = self.read_parameter(self.ui_page.elec_gap_input)  # The target gap between electrodes
        self.electrode_extrusion_height = 0.5  # The height of the electrodes
        
        # Initialize variables for connector Handling
        self.select_connnector_faces_mode = False  # Track whether connector face selection mode is active
        self.selected_connector_faces = set()
        self.selected_connector_points = []
        self.connector_radius = self.read_parameter(self.ui_page.conn_diameter_input)/2  # The radius of the connectors
        self.target_connector_gap = self.read_parameter(self.ui_page.conn_gap_input)  # The target gap between connectors
        self.connector_extrusion_height = 0.5  # The height of the connectors

        # Initialize variables for routing traces
        self.trace_radius = self.read_parameter(self.ui_page.trace_diameter_input)/2  # The radius of the routing traces
        self.routing_clearance = self.read_parameter(self.ui_page.trace_clearance_input)  # The clearance between the routing traces and the electrodes/connectors
        self.routing_paths = []  # The paths of the routing traces

        # Variables for tools
        self.conductive_components = None # The mesh representing the routing traces

        self.export_all_conductive_meshes = self.ui_page.export_all_conductive_meshes_checkbox.isChecked()
        # Connect interactor event
        self.ui_page.plotter.iren.add_observer("LeftButtonPressEvent", self.on_left_button_press)

    def read_parameter(self, line_edit):
        #get the updated parameters from the UI
        try:
            value =  float(line_edit.text().strip("mm"))
            return value
        except:
            self.ui_page.show_warning("Invalid Input!. Please enter a valid numerical value for the parameter")
            return None

    def update_parameters(self):
        #get the electrode radius
        in_value = self.read_parameter(self.ui_page.elec_diameter_input)
        if in_value is not None:
            self.electrode_radius = in_value/2
        else:
            self.ui_page.elec_diameter_input.setText(str(self.electrode_radius*2) + "mm")
        #get the electrode gap
        in_value = self.read_parameter(self.ui_page.elec_gap_input)
        if in_value is not None:
            self.target_electrode_gap = in_value
        else:
            self.ui_page.elec_gap_input.setText(str(self.target_electrode_gap) + "mm")
        #get the connector radius
        in_value = self.read_parameter(self.ui_page.conn_diameter_input)
        if in_value is not None:
            self.connector_radius = in_value/2
        else:
            self.ui_page.conn_diameter_input.setText(str(self.connector_radius*2) + "mm")
        #get the connector gap
        in_value = self.read_parameter(self.ui_page.conn_gap_input)
        if in_value is not None:
            self.target_connector_gap = in_value
        else:
            self.ui_page.conn_gap_input.setText(str(self.target_connector_gap) + "mm")
        #get the trace radius
        in_value = self.read_parameter(self.ui_page.trace_diameter_input)
        if in_value is not None:
            self.trace_radius = in_value/2
        else:
            self.ui_page.trace_diameter_input.setText(str(self.trace_radius*2) + "mm")
        #get the trace clearance
        in_value = self.read_parameter(self.ui_page.trace_clearance_input)
        if in_value is not None:
            self.routing_clearance = in_value
        else:
            self.ui_page.trace_clearance_input.setText(str(self.routing_clearance) + "mm")
        #get the export all conductive meshes checkbox
        self.export_all_conductive_meshes = self.ui_page.export_all_conductive_meshes_checkbox.isChecked()

    # -------------------------------------------BASIC CONTROLS---------------------------------------------------------------------------
    def enable_electrode_face_mode(self):
        self.select_electrode_faces_mode = True
        self.select_connnector_faces_mode = False
    
    def enable_connector_face_mode(self):
        self.select_connnector_faces_mode = True
        self.select_electrode_faces_mode = False
    
    def finish_face_selection(self):
        self.select_electrode_faces_mode = False
        self.select_connnector_faces_mode = False
        self.create_3D_routing_paths(smoothing_iterations=3)
    
    def reset_controller_memory(self):
        self.selected_connector_faces.clear()
        self.selected_electrode_faces.clear()
        self.selected_electrode_points = []
        self.selected_connector_points = []
        self.routing_paths = []
        self.conductive_components = None
    # -------------------------------------------MOUSE CONTROLS ---------------------------------------------------------------------
    def on_left_button_press(self, obj, event):
        if self.select_electrode_faces_mode:
            click_position = self.ui_page.plotter.iren.get_event_position()
            self.select_face(click_position, mode='E') # Passes red as default face color
        elif self.select_connnector_faces_mode:
            click_position = self.ui_page.plotter.iren.get_event_position()
            self.select_face(click_position, mode='C') # Passes green as default face color
        #Continue with the default interaction behavior
        self.ui_page.plotter.iren.get_interactor_style().OnLeftButtonDown()

    # -------------------------------------------FILE HANDLING-----------------------------------------------------------------------------
    def load_mesh(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
                                            self.ui_page,
                                            "Open Mesh File",
                                            "",
                                            "Mesh Files (*.stl *.obj);;STL Files (*.stl);;OBJ Files (*.obj);;All Files (*)",
                                            options=options)
        if filename:
            mesh_pv = pv.read(filename)
            mesh_pv = mesh_pv.triangulate()  # Ensure the mesh is triangulated

            # Subdivide the mesh to ensure uniform triangle size
            # mesh_pv = mesh_pv.subdivide(1, 'loop')  # Subdivide the mesh to ensure no large faces
            mesh_pv = mesh_pv.subdivide_adaptive(max_edge_len = 0.5)  # Subdivide the mesh to have triangles at most 0.4mm edge length
            
            self.mesh = mesh_pv
            self.original_mesh = self.mesh.copy()
            self.ui_page.plotter.load_mesh_to_canvas(self.mesh)
      
    def generate_output_files(self, main_mesh, routing_mesh):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
                                    self.ui_page,
                                    "Save Edited Mesh",
                                    "",
                                    "OBJ Files (*.obj);;All Files (*)",  # Only show .obj by default,
                                    options=options)
        if filename:
            filename = filename[:-4]  # Remove .stl extension if present
            # Generate the filenames
            main_mesh_filename = f"{filename}_main_mesh.obj"
            routing_mesh_filename = f"{filename}_routing_traces.obj"

            # create the json file for the cordinates of the electrodes and connectors
            json_data = self.create_json_coordinates()
            json_filename = f"{filename}_coordinates.json"

        # Save the meshes
        try:
            routing_mesh.save(routing_mesh_filename)
            main_mesh.save(main_mesh_filename)
            with open(json_filename, 'w') as json_file:
                json.dump(json_data, json_file, indent=4) # Save the JSON data with indentation
            
            QMessageBox.information(self.ui_page, "Success", "Files saved successfully!")
        except Exception as e:
            QMessageBox.critical(self.ui_page, "Error", f"Failed to save meshes:\n{e}")

    def create_json_coordinates(self):
        # Convert each tuple into a dictionary with "x" and "y" keys
        electrodes = [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in self.selected_electrode_points]
        connectors = [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in self.selected_connector_points]
        mapping_function = [i for i in range(len(self.selected_electrode_points))]
        # Create a dictionary structure to store both lists
        data = {
            "electrodes": electrodes,
            "connectors": connectors,
            "Mapping_func": mapping_function,
            "electrode_radius": self.electrode_radius
        }
        return data

    # -------------------------------------------MESH OPERATIONS -----------------------------------------------------------------------------
    def simplify_mesh(self):
        """
        Reduces the number of triangles in the mesh by the given percentage
        reduce_percentage: reduction percentage
        """
        reduction_percentage = self.ui_page.simplify_slider.value()

        self.ui_page.slider_value_label.setText(f'{reduction_percentage}%')  # Update slider value label
        self.reset_controller_memory() # Reset the controller memory to clear any existing outputs and generations

        self.ui_page.plotter.save_camera_view()
        if self.mesh:
            # target_reduction = 1 - (reduction_percentage / 100)
            # self.mesh = self.original_mesh.decimate(target_reduction)
            
            vertices_count = self.original_mesh.n_points

            target_vertices = int(vertices_count * reduction_percentage / 100)
            if target_vertices == 0:
                target_vertices = 1
            else:
                # 1. Initialize clustering
                cluster = pyacvd.Clustering(self.original_mesh)
                cluster.cluster(target_vertices)
                self.mesh = cluster.create_mesh()
                
        self.ui_page.plotter.update_display(self.mesh, _color='lightblue', _show_edges=True, _edge_color='black') # Update the display with the simplified mesh.
        self.ui_page.plotter.restore_camera_view()
    
    def snap_points_to_mesh_surface(self, mesh, points):
        """
        Snap the given points to the closest location on the surface of the original mesh using VTK.

        :param original_mesh: The original mesh (PyVista PolyData).
        :param points: The points to be snapped to the mesh surface.
        :return: Array of points snapped to the surface of the original mesh.
        """
        #check if points is empty
        if len(points) == 0:
            return np.array([])
        # Convert PyVista mesh to VTK format
        vtk_mesh = mesh.cast_to_unstructured_grid()

        # Initialize vtkCellLocator
        cell_locator = vtk.vtkCellLocator()
        cell_locator.SetDataSet(vtk_mesh)
        cell_locator.BuildLocator()

        # Prepare an array to hold the snapped points
        snapped_points = np.zeros_like(points)

        # Iterate over each point and find the closest point on the surface
        for i, point in enumerate(points):
            closest_point = [0.0, 0.0, 0.0]
            cell_id = vtk.mutable(0)
            sub_id = vtk.mutable(0)
            dist2 = vtk.mutable(0.0)

            # Find the closest point on the mesh surface
            cell_locator.FindClosestPoint(point, closest_point, cell_id, sub_id, dist2)
            snapped_points[i] = closest_point
        return snapped_points
    
    def generate_conductive_component_meshes(self, only_routed=False):
        conductive_meshes = []
        if only_routed: # Generate meshes only for the routed paths and connected electrodes/connectors
            for path in self.routing_paths:
                #------------------------------------creating the electrode -------------------------------------------------------
                # Find the closest cell (face) on the mesh to get the normal
                closest_cell_id = self.original_mesh.find_closest_cell(path[0])
                normal = self.original_mesh.cell_normals[closest_cell_id]
                # Use the normal as the direction for the cylinder
                direction = normal
                # Create the cylinder
                cylinder = pv.Cylinder(center=path[0], direction=direction, radius=self.electrode_radius, height=self.electrode_extrusion_height)
                conductive_meshes.append(cylinder)

                #-----------------------------------creating the connectr -------------------------------------------------
                # Find the closest cell (face) on the mesh to get the normal
                closest_cell_id = self.original_mesh.find_closest_cell(path[-1])
                normal = self.original_mesh.cell_normals[closest_cell_id]
                # Use the normal as the direction for the cylinder
                direction = normal
                # Create the cylinder
                cylinder = pv.Cylinder(center=path[-1], direction=direction, radius=self.connector_radius, height=self.connector_extrusion_height) #Increase the connector radius
                conductive_meshes.append(cylinder)

                #------------------------------------creating the 3D trace ---------------------------------------------------
                # Create a tube along the path
                trace_mesh = self.create_tube_along_path(path, radius=self.trace_radius)
                conductive_meshes.append(trace_mesh)
        else: # Generate meshes for all electrodes, connectors, and routing traces
            # Generate meshes for electrodes
            for electrode in self.selected_electrode_points:
                # Find the closest cell (face) on the mesh to get the normal
                closest_cell_id = self.original_mesh.find_closest_cell(electrode)
                normal = self.original_mesh.cell_normals[closest_cell_id]
                # Use the normal as the direction for the cylinder
                direction = normal
                # Create the cylinder
                cylinder = pv.Cylinder(center=electrode, direction=direction, radius=self.electrode_radius, height=self.electrode_extrusion_height)
                conductive_meshes.append(cylinder)
            # Generate meshes for connectors
            for connector in self.selected_connector_points:
                # Find the closest cell (face) on the mesh to get the normal
                closest_cell_id = self.original_mesh.find_closest_cell(connector)
                normal = self.original_mesh.cell_normals[closest_cell_id]
                # Use the normal as the direction for the cylinder
                direction = normal
                # Create the cylinder
                cylinder = pv.Cylinder(center=connector, direction=direction, radius=self.connector_radius, height=self.connector_extrusion_height)
                conductive_meshes.append(cylinder)
            # Generate meshes for routing traces
            for path in self.routing_paths:
                # Create a tube along the path
                trace_mesh = self.create_tube_along_path(path, radius=self.trace_radius)
                conductive_meshes.append(trace_mesh)
        
        return conductive_meshes
    
    def prepare_export_meshes(self):
        # get the conductive meshes to import based on the user selection on checkbox
        self.conductive_components = self.generate_conductive_component_meshes(only_routed=self.export_all_conductive_meshes)

        if self.original_mesh is not None and self.conductive_components is not None:
            # Convert the combined mesh to PolyData (if necessary)
            if not isinstance(self.original_mesh, pv.PolyData):
                self.original_mesh = self.original_mesh.extract_surface()
            # Clean the meshes to remove any bad geometry
            self.original_mesh = self.original_mesh.clean()

            # combine the tool meshes
            combined_tools = pv.MultiBlock(self.conductive_components).combine()
            if not isinstance(combined_tools, pv.PolyData):
                    combined_tools = combined_tools.extract_surface()

            # Save the edited mesh to a files
            self.generate_output_files(self.original_mesh, combined_tools)
    
# ------------------------------------------- TASK HANDLING ---------------------------------------------------------------------------
    def select_face(self, click_position, mode = 'E'):
        """
        Selects a face on the mesh based on the click position.
        click_position: The position of the click in screen coordinates.
        mode: The mode of selection ('E' for electrode, 'C' for connector)
        color: The color to use when highlighting the selected face.
        """
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:            
            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.0005)

            # Perform the pick operation
            picker.Pick(click_position[0], click_position[1], 0, self.ui_page.plotter.renderer)

            if picker.GetCellId() != -1:
                picked_face = picker.GetCellId()
                face_normal = self.mesh.cell_normals[picked_face]
                camera_direction = self.ui_page.plotter.camera.GetDirectionOfProjection()
                # Ensure we're selecting the face that is oriented towards the camera
                if np.dot(face_normal, camera_direction) < 0:
                    if mode == 'E':
                        if picked_face in self.selected_electrode_faces:
                            self.selected_electrode_faces.remove(picked_face)
                        else:
                            self.selected_electrode_faces.add(picked_face)
                    elif mode == 'C':
                        if picked_face in self.selected_connector_faces:
                            self.selected_connector_faces.remove(picked_face)
                        else:
                            self.selected_connector_faces.add(picked_face)
                
                # Clear the existing display and add the main mesh
                self.ui_page.plotter.save_camera_view()
                self.ui_page.plotter.update_display(self.mesh, _color='lightblue', _show_edges=True, _edge_color='black') # Update the display the mesh object
                #Updating the view with the new selections
                self.ui_page.plotter.restore_camera_view()
                if self.selected_electrode_faces:
                    electrode_faces = self.mesh.extract_cells(list(self.selected_electrode_faces))
                    electrode_faces = electrode_faces.clean()

                    self.ui_page.plotter.append_display(electrode_faces, _color='red', _show_edges=True, _edge_color='black') # append the display the selected faces mesh
                    self.selected_electrode_points = self.populate_equidistant_points_on_surface(electrode_faces, self.target_electrode_gap)  # Populate equidistant points on the selected faces and update the selected points list
                    #visualize the electrodes
                    self.visualize_electrodes(self.selected_electrode_points, _radius=self.electrode_radius, _height=self.electrode_extrusion_height, _color='black', _opacity=0.9)
                if self.selected_connector_faces:
                    connector_faces = self.mesh.extract_cells(list(self.selected_connector_faces))
                    connector_faces = connector_faces.clean()
                    self.ui_page.plotter.append_display(connector_faces, _color='green', _show_edges=True, _edge_color='black') # append display the selected faces mesh
                    self.selected_connector_points = self.populate_equidistant_points_on_surface(connector_faces, self.target_connector_gap)
                    #visualize the connectors
                    self.visualize_electrodes(self.selected_connector_points, _radius=self.connector_radius, _height=self.connector_extrusion_height, _color='black', _opacity=0.9)
                
    def populate_equidistant_points_on_surface(self, mesh_surface, target_point_gap):
        """
        Populates an equidistant set of points within the selected regions.
        :param plotter: The PyVista plotter object used to display the points.
        :param radius: The minimum distance between points (controls the spacing).
        """
        def seperate_unconnected_meshes(mesh_group):
            """
            Extracts the selected faces from the mesh and separates them into distinct connected components.
            mesh: The surface mesh group to extract unconnected faces from.
            :return: A list of sub-meshes, each representing a distinct group of connected faces.
            """
            # Find connected components in the mesh
            connected_components = mesh_group.connectivity(split_bodies=True)
            # Debug: Check how many regions were identified
            region_ids = connected_components.cell_data['RegionId']
            unique_regions = np.unique(region_ids)

            # Separate the connected components into distinct sub-meshes
            sub_meshes = []
            for region_id in unique_regions:
                # Extract faces belonging to this region
                mask = region_ids == region_id
                sub_mesh = connected_components.extract_cells(mask)
                sub_meshes.append(sub_mesh.clean())  # Clean each sub-mesh to remove unused vertices
            return sub_meshes
    
        def subdivide_contour_by_length(contour, max_segment_length):
            if contour.n_points < 2:
                return pv.PolyData()

            # Extract the points and lines
            points = contour.points
            lines = contour.lines.reshape(-1, 3)[:, 1:]

            subdivided_points = []
            for line in lines:
                pt1 = points[line[0]]
                pt2 = points[line[1]]
                segment_length = np.linalg.norm(pt2 - pt1)
                num_subdivisions = max(int(segment_length / max_segment_length) + 1, 2)
                t_values = np.linspace(0, 1, num_subdivisions)
                segment_points = np.outer(1 - t_values, pt1) + np.outer(t_values, pt2)
                subdivided_points.append(segment_points)

            if subdivided_points:
                subdivided_points = np.vstack(subdivided_points)
                subdivided_contour = pv.PolyData(subdivided_points)
            else:
                subdivided_contour = pv.PolyData()

            return subdivided_contour

        def compute_edge_lengths(poly):
            """Compute all edge lengths in a triangulated PolyData mesh."""
            faces = poly.faces.reshape(-1, 4)  # each row: [3, i0, i1, i2]
            pts = poly.points
            lengths = []
            for f in faces:
                if f[0] != 3:  # skip non-triangle cells
                    continue
                i0, i1, i2 = f[1], f[2], f[3]
                p0, p1, p2 = pts[i0], pts[i1], pts[i2]
                e01 = np.linalg.norm(p0 - p1)
                e12 = np.linalg.norm(p1 - p2)
                e20 = np.linalg.norm(p2 - p0)
                lengths.extend([e01, e12, e20])
            return np.array(lengths)

        def estimate_vertex_count(mesh_area, target_edge_length):
            """
            Estimate number of vertices needed to achieve
            an average edge length near 'target_edge_length'.
            """
            A_tri = (np.sqrt(3) / 4) * (target_edge_length ** 2)
            # Approx number of triangles:
            num_faces_est = mesh_area / A_tri
            # For typical meshes, #faces ~ 2 * #vertices
            num_vertices_est = num_faces_est / 2.0
            return int(round(num_vertices_est))

        selected_face_groups = seperate_unconnected_meshes(mesh_surface)
        snapped_points_all = []
        # for selected_faces in selected_face_groups:
        #     # -----------------------------------------------------------DUMMY CODE TO VISUALIZE THE POINTS----------------------------------------------------------
        #     length_u = target_point_gap   # length of grid along U
        #     length_v = target_point_gap   # length of grid along V
        #     max_segment_length = 0.1      # Maximum segment length for grid lines
        #     tolerance = 0.3               # Tolerance for snapping points to grid lines
            
        #     selected_faces.texture_map_to_plane(inplace=True)

        #     # Get texture coordinates
        #     uv_coords = selected_faces.point_data['Texture Coordinates']
        #     u_coords = uv_coords[:, 0]
        #     v_coords = uv_coords[:, 1]

        #     # Estimate physical lengths along U and V directions
        #     # Assuming texture coordinates are proportional to physical distances
        #     # Get points at min and max U
        #     min_u = u_coords.min()
        #     max_u = u_coords.max()
        #     min_u_points = selected_faces.points[np.isclose(u_coords, min_u)]
        #     max_u_points = selected_faces.points[np.isclose(u_coords, max_u)]
        #     if min_u_points.size == 0 or max_u_points.size == 0:
        #         raise ValueError("Could not find points at min or max U values.")

        #     # Compute approximate physical length along U
        #     # For simplicity, take the average distance between min_u_points and max_u_points
        #     u_length = np.mean(np.linalg.norm(max_u_points - min_u_points, axis=1))

        #     # Similarly for V
        #     min_v = v_coords.min()
        #     max_v = v_coords.max()
        #     min_v_points = selected_faces.points[np.isclose(v_coords, min_v)]
        #     max_v_points = selected_faces.points[np.isclose(v_coords, max_v)]
        #     if min_v_points.size == 0 or max_v_points.size == 0:
        #         raise ValueError("Could not find points at min or max V values.")

        #     # Compute approximate physical length along V
        #     v_length = np.mean(np.linalg.norm(max_v_points - min_v_points, axis=1))

        #     # Calculate the number of grid lines based on specified lengths
        #     num_u_lines = max(int(u_length / length_u), 2)
        #     num_v_lines = max(int(v_length / length_v), 2)
            
        #     # Generate contour levels for U and V
        #     u_levels = np.linspace(min_u, max_u, num_u_lines)
        #     v_levels = np.linspace(min_v, max_v, num_v_lines)

        #     # Generate grid lines along U and V directions
        #     u_contours = [selected_faces.contour(isosurfaces=[level], scalars=u_coords) for level in u_levels]
        #     v_contours = [selected_faces.contour(isosurfaces=[level], scalars=v_coords) for level in v_levels]
            
        #     # Subdivide contours based on maximum segment length
        #     u_contours_subdivided = [subdivide_contour_by_length(contour, max_segment_length) for contour in u_contours]
        #     v_contours_subdivided = [subdivide_contour_by_length(contour, max_segment_length) for contour in v_contours]
        
        #     # Find grid points by closest point matching using cKDTree
        #     grid_points_coords = []
        #     for u_contour in u_contours_subdivided:
        #         if u_contour.n_points == 0:
        #             continue
        #         u_points = u_contour.points
        #         u_tree = cKDTree(u_points)
        #         for v_contour in v_contours_subdivided:
        #             if v_contour.n_points == 0:
        #                 continue
        #             v_points = v_contour.points
        #             # Query u_tree with v_points to find nearest neighbors
        #             distances, indices = u_tree.query(v_points)
        #             min_idx = np.argmin(distances)
        #             min_distance = distances[min_idx]
        #             if min_distance < tolerance:
        #                 # Get the corresponding points
        #                 point_u = u_points[indices[min_idx]]
        #                 point_v = v_points[min_idx]
        #                 # Choose either midpoint or one of the points as grid point
        #                 grid_point = (point_u + point_v) / 2.0
        #                 grid_points_coords.append(grid_point)
        #     # Combine all grid points and remove duplicates
        #     if grid_points_coords:
        #         grid_points_coords = np.vstack(grid_points_coords)
        #         grid_points_coords = np.unique(grid_points_coords, axis=0)
        #         #-----------------------------------
        #         snapped_points = self.snap_points_to_mesh_surface(self.original_mesh, grid_points_coords)
        #         snapped_points_all.extend(snapped_points)

        #     # Combine the contours into a MultiBlock dataset
        #     grid_lines = pv.MultiBlock(u_contours + v_contours)

        #     # Add the grid lines to the plotter
        #     self.ui_page.plotter.add_mesh(grid_lines, color='black', line_width=5, opacity=1)

        # Desired average edge length
        L_target = target_point_gap  # in mm

        for selected_faces in selected_face_groups:
            # Convert to PolyData
            surface_mesh = selected_faces.extract_surface()

            # Estimate the number of vertices needed to achieve the target edge length
            mesh_area = surface_mesh.area
            N_est = estimate_vertex_count(mesh_area, L_target)
            if N_est == 0:
                continue
            elif N_est < 3:
                N_est = 3

            #subdived the mesh to have a more accurate remeshing
            subdivided_mesh = surface_mesh.subdivide_adaptive(max_edge_len = 0.2)
            # subdivided_mesh = surface_mesh.subdivide(1, 'loop')  # Subdivide the mesh to ensure no large faces

            max_iterations = 5
            tolerance_ratio = 0.05  # +/- 5%
            for it in range(max_iterations):
                # Clustering from the already-subdivided mesh
                acvd = pyacvd.Clustering(subdivided_mesh)
                acvd.cluster(N_est)
                remeshed = acvd.create_mesh()

                if remeshed.n_cells == 0: # Avoid empty mesh
                    break

                # Measure mean edge length
                edge_lengths = compute_edge_lengths(remeshed)
                mean_edge = np.nanmean(edge_lengths) # ignore NaNs

                # Check convergence
                ratio = mean_edge / L_target
                if abs(ratio - 1.0) < tolerance_ratio:
                    # print(f"Converged! Mean edge is within +/- {tolerance_ratio*100}% of {L_target}\n")
                    break

                # Adjust N_est based on ratio
                # e.g. scale by ratio^2 => #vertices ~ 1 / edge^2
                new_N_est = int(round(N_est * (ratio ** 2)))
                new_N_est = max(new_N_est, 3)  # avoid zero or negative
                N_est = new_N_est

            # Check if remeshed is empty
            if remeshed.n_cells == 0:
                continue

            # Snap the points to the original mesh if the edge length is close to the target
            if abs(ratio - 1.0) < tolerance_ratio:
                snapped_points = self.snap_points_to_mesh_surface(self.original_mesh, remeshed.points)
                snapped_points_all.extend(snapped_points)
            else:
                snapped_points = self.snap_points_to_mesh_surface(self.original_mesh, np.array([remeshed.points[0]])) # Snap the first point only
                snapped_points_all.extend(snapped_points)

        return snapped_points_all

    def visualize_electrodes(self, points, _radius, _height, _color='blue', _opacity=0.8):
        if not points:
            return
        cylinder_meshes = []
        for point in points:
            # Find the closest cell (face) on the mesh to get the normal
            closest_cell_id = self.mesh.find_closest_cell(point)
            normal = self.mesh.cell_normals[closest_cell_id]

            # Use the normal as the direction for the cylinder
            direction = normal

            # Create the cylinder
            cylinder = pv.Cylinder(center=point, direction=direction, radius=_radius, height=_height)
            cylinder_meshes.append(cylinder)

        # Combine all cylinders into one mesh and display
        combined_cylinders = pv.MultiBlock(cylinder_meshes).combine()

        # Display the combined cylinders on the plotter
        self.ui_page.plotter.append_display(combined_cylinders, _color=_color, _opacity=_opacity)  # Append the display with the new mesh
    
    def visualize_routing_traces(self, paths, radius, color='black', opacity=1):
        path_meshes = []
        for path in paths:
            # Create a tube along the path
            trace_mesh = self.create_tube_along_path(path, radius=radius)
            path_meshes.append(trace_mesh)
        # Combine all tubes into one mesh and display
        combined_tubes = pv.MultiBlock(path_meshes).combine()

        # Display the combined tubes on the plotter
        self.ui_page.plotter.append_display(combined_tubes, _color=color, _opacity=opacity)  # Append the display with the new mesh


    def create_3D_routing_paths(self, smoothing_iterations):
        def get_unrouted_electrodes_and_connectors(electrode_points, connector_points):
            electrodes = []
            connectors = []
            for electrode in electrode_points:
                for path in self.routing_paths:
                    if np.allclose(path[0], electrode, atol=1e-3):
                        break
                    if np.allclose(path[-1], electrode, atol=1e-3):
                        break
                else:
                    electrodes.append(electrode)
                
            for connector in connector_points:
                for path in self.routing_paths:
                    if np.allclose(path[0], connector, atol=1e-3):
                        break
                    if np.allclose(path[-1], connector, atol=1e-3):
                        break
                else:
                    connectors.append(connector)
                
            return electrodes, connectors

        # Show the progress dialog
        progress_dialog = self.ui_page.show_progress_window()
        #calculations for the progreee bar
        
        progress_dialog.setValue(15)  # Set the initial progress value
        QApplication.processEvents()  # Keep the GUI responsive
        print()
        # Perform routing and create conection paths ------------------------------------------------------------
        router = ThreeDRouter(self.original_mesh,
                              self.trace_radius,
                              self.electrode_radius,
                              self.connector_radius,
                              self.routing_clearance)
        
        # check what electrodes and connectros have already been routed
        unrouted_electrodes, unrouted_connectors = get_unrouted_electrodes_and_connectors(self.selected_electrode_points, self.selected_connector_points)

        print(f"Unrouted electrodes: {len(unrouted_electrodes)}")
        print(f"Unrouted connectors: {len(unrouted_connectors)}")

        if len(unrouted_electrodes) > 0 and len(unrouted_connectors) > 0:
            self.routing_paths = router.route_connection_paths(unrouted_electrodes,
                                                                unrouted_connectors,
                                                                self.routing_paths.copy(),
                                                                step = self.trace_radius*2 + self.routing_clearance)
            # Smooth the paths
            self.routing_paths = [self.smooth_path(path, smoothing_iterations) for path in self.routing_paths]
        else:
            self.ui_page.show_warning("There are no new electrodes or connectors to route. Please select new electrodes or connectors.")
        
        #Showing a translucscent mesh to make sure we see the internal routing traces
        self.ui_page.plotter.update_display(mesh = self.original_mesh, _color='black', _show_edges=True, _edge_color='black', _opacity=0.3)
        
        # add the electrodes and connectors to the plotter
        self.visualize_electrodes(self.selected_electrode_points, _radius=self.electrode_radius, _height=self.electrode_extrusion_height, _color='black', _opacity=1)
        self.visualize_electrodes(self.selected_connector_points, _radius=self.connector_radius, _height=self.connector_extrusion_height, _color='black', _opacity=1)

        # add the routing traces to the plotter
        self.visualize_routing_traces(self.routing_paths, radius=self.trace_radius, color='black', opacity=1)

        # Update the progress dialog
        progress_dialog.setValue(100)  # Ensure the progress reaches 100%
        QApplication.processEvents()   # Keep the GUI responsive
        progress_dialog.close()  # Close the dialog when done

#--------------------------------------------- 3D TUBE PATH CREATION ---------------------------------------------------------------------------    
    def smooth_path(self, path_points, iterations=3):
        """
        Smooths a path using Chaikin's Algorithm, preserving the original endpoints.
        :param path_points: The original points defining the path.
        :param iterations: The number of iterations of smoothing to apply.
        :return: A set of smoothed points.
        """
        for _ in range(iterations):
            new_points = [path_points[0]]  # Start with the first point
            for i in range(len(path_points) - 1):
                p0 = path_points[i]
                p1 = path_points[i + 1]

                # Calculate the new points based on the current segment
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1

                new_points.extend([q, r])

            new_points.append(path_points[-1])  # End with the last point
            path_points = np.array(new_points)
        
        return path_points

    def create_tube_along_path(self, path_points, radius):
        """
        Creates a tube along a given path, optionally smoothing the path first.
        :param path_points: The original points defining the path.
        :param radius: The radius of the tube.
        :param smoothing_factor: A value between 0 and 1 that determines the amount of smoothing.
        :return: The created tube mesh.
        """
        if len(path_points) < 2:
            raise ValueError("Path must have at least two points.")

        # Create a PolyData object for the path
        path = pv.PolyData(path_points)

        # Generate a line connecting the points
        path_lines = np.arange(0, len(path_points), dtype=np.int32)
        path_lines = np.insert(path_lines, 0, len(path_lines))     # Insert the number of points at the beginning (VTK's internal requirement)
        path.lines = path_lines
        path = path.tube(radius=radius, n_sides=20)  # Create a tube along the path
        return path



# ------------------------------------------- PATH SEARCH ON MESH ------------------------------------------------------------------
class ThreeDRouter:
    def __init__(self, mesh, track_radius, electrode_radius, connector_radius, routing_clearance):
        """
        Initialize the PointInMeshChecker with a given mesh.

        :param mesh: The input mesh (PyVista PolyData or UnstructuredGrid).
        """
        # Convert the PyVista mesh to vtkPolyData if necessary
        if not isinstance(mesh, pv.PolyData):
            mesh = mesh.extract_surface()
        
        # 2. Fix any issues with the mesh
        meshfixer = MeshFix(mesh)
        meshfixer.repair(verbose=False)
        mesh = meshfixer.mesh
            
        self.mesh = mesh
        self.electrode_radius = electrode_radius  # The radius of the electrodes
        self.connector_radius = connector_radius  # The radius of the connectors
        self.track_radius = track_radius              # The radius of the track to be created
        self.routing_clearance = routing_clearance      # The clearance between the routing traces and the electrodes/connectors

        # Initialize the set of occupied points
        self.occupied_points = set()
        self.keep_out_meshes = []
        self.paths = []

    # Check if the given tuple is in the set within the tolerance
    def tuple_inside_tolerance(self, given_tuple, tuple_set, tolerance = 50e-3):
        for t in tuple_set:
            if all(abs(a - b) <= tolerance for a, b in zip(given_tuple, t)):
                return t
        return None
    
    def is_valid_point(self, point):
        """
        Check if a single point is inside the mesh.

        :param point: The point to test (array-like with 3 coordinates).
        :return: True if the point is inside the mesh, False otherwise.
        """
        # check if the point is inside the main mesh
        points_poly = pv.PolyData(point, force_float=False)
        select_main_mesh = points_poly.select_enclosed_points(self.mesh)
        if not select_main_mesh['SelectedPoints'][0]:
            return False

        # # check if at safe distance from the mesh surface
        # closest_point_id = self.mesh.find_closest_point(point)
        # closest_point = self.mesh.points[closest_point_id]
        # # Compute the Euclidean distance between the point and the closest surface point
        # distance = np.linalg.norm(point - closest_point)
        # if distance < self.track_radius*2:  # IMPORTANT: THIS VALUE CAN LEAD TO NOT FINDING A VALID POINT
        #     return False

        #check the keep out mesh
        for keep_out_mesh in self.keep_out_meshes:
            closest_point_id = keep_out_mesh.find_closest_point(point)
            closest_point = keep_out_mesh.points[closest_point_id]
            distance = np.linalg.norm(point - closest_point)
            if distance < self.track_radius + self.routing_clearance:
                return False 
            
        return self.tuple_inside_tolerance(tuple(point), self.occupied_points) == None
    
    # ---------------------------------------------------------
    def snap_to_mesh_grid(self, point, step, mesh = None):
        """snaps the point to the closest grid point"""
        # Snap the point to the closest grid point
        x = round(point[0] / step) * step
        y = round(point[1] / step) * step
        z = round(point[2] / step) * step
        
        round_point = np.array([x, y, z])

        # Find the closest cell in the mesh and get its normal vector
        if mesh is not None:
            closest_cell_id = mesh.find_closest_cell(point)
            cell_normal = mesh.cell_normals[closest_cell_id]  # Get the normal vector of the closest cell

            # Normalize the normal vector
            cell_normal = cell_normal / np.linalg.norm(cell_normal)
        else:
            raise ValueError("Mesh is required to compute the normal direction.")
        
        # Now make sure the point is inside the mesh
        #  Generate all 26 possible directions in 3D space
        steps = [
            np.array([dx, dy, dz]) * step
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            for dz in [-1, 0, 1]
        ]

        # Find the point in the direction that is most aligned with the normal vector
        best_point = round_point
        max_alignment = -float('inf')  # Start with the lowest possible value

        for step in steps:
            neighbor = round_point + step
            if not self.is_valid_point(neighbor): # Skip invalid points
                continue

            direction = (neighbor - point) / np.linalg.norm(neighbor - point) #the movement direction vector

            # Compute alignment (dot product) between the direction and the normal vector
            alignment = np.abs(np.dot(direction, cell_normal))
            
            # Check if this direction is more aligned with the normal than the previous ones
            if alignment > max_alignment:
                max_alignment = alignment
                best_point = neighbor
        # Return the snapped point in the best direction
        if self.is_valid_point(best_point):
            return best_point
        else:
            return None

    def heuristic_euclidean(self, p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))
    
    def get_neighbors(self, point, step):
        #  Generate all 26 possible directions in 3D space
        directions = [
            np.array([dx, dy, dz]) * step
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
            for dz in [-1, 0, 1]
            if not (dx == 0 and dy == 0 and dz == 0)
        ]

        neighbors = []
        for direction in directions:
            neighbor = np.array(point) + direction
            neighbor_midpoint = (np.array(point) + neighbor) / 2
            if self.is_valid_point(neighbor) and self.is_valid_point(neighbor_midpoint):
                neighbors.append(tuple(neighbor))   
        return neighbors

    def a_star(self, start, end, step, similartiyt_tolerance = 50e-3):
        start = tuple(start)
        end = tuple(end)

        queue = [] 
        g_costs = {start: 0}                                     # cost developed by traversing
        f_costs = {start: self.heuristic_euclidean(start, end)}  # cost based on the distance to travel
        previous_nodes = {start: None}
        heapq.heappush(queue, (f_costs[start], start))
        
        while queue:
            current_f_cost, current_point = heapq.heappop(queue)
            if np.linalg.norm(np.array(current_point) - np.array(end)) < similartiyt_tolerance:
                path = []
                while previous_nodes[current_point] is not None:
                    path.append(np.array(current_point))
                    current_point = previous_nodes[current_point]
                path.append(np.array(start))
                path.reverse()
                return path
            
            for neighbor in self.get_neighbors(current_point, step):
                tentative_g_cost = g_costs[current_point] + 1#np.linalg.norm(np.array(current_point) - np.array(neighbor))
                similar_point = self.tuple_inside_tolerance(neighbor, g_costs, similartiyt_tolerance)
                if similar_point is None: #there are no similar points
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

    # Let's start the path finding
    def route_connection_paths(self, start_points, end_points, existing_paths, step):
        self.paths = existing_paths
        missed_ends = []
        original_end_points = end_points.copy()
        original_start_points = start_points.copy()
        while start_points:
            if not end_points:
                return self.paths
            current_start = start_points.pop(0)
            current_end = end_points.pop(0)

            #-------------------------------------------------------- update the keep out polygons for each iteration --------------------------------
            self.keep_out_meshes = []
            # creating the keep out mesh from the tracks
            for path in self.paths:
                path_poly = pv.PolyData(path)
                # Generate a line connecting the points
                path_lines = np.arange(0, len(path), dtype=np.int32)
                path_lines = np.insert(path_lines, 0, len(path_lines))     # Insert the number of points at the beginning (VTK's internal requirement)
                path_poly.lines = path_lines
                path_poly = path_poly.tube(radius=self.track_radius+1, n_sides=20, capping=True)  # Create a tube along the path
                self.keep_out_meshes.append(path_poly)

            #Add the electrode start points to the keep out meshes as spheres
            for point in original_start_points:
                sphere = pv.Sphere(center=point, radius=self.electrode_radius + self.track_radius)
                #check if current end point is in this shere
                points_poly = pv.PolyData(current_start, force_float=False)
                select = points_poly.select_enclosed_points(sphere)
                if not select['SelectedPoints'][0]:
                    self.keep_out_meshes.append(sphere)

            # Add the connectors to the keep out meshes by making a sphere around the point
            for point in original_end_points:
                sphere = pv.Sphere(center=point, radius=self.connector_radius + self.track_radius)
                #check if current end point is in this shere
                points_poly = pv.PolyData(current_end, force_float=False)
                select = points_poly.select_enclosed_points(sphere)
                if not select['SelectedPoints'][0]:
                    self.keep_out_meshes.append(sphere)
                    
            #-------------------------------------------------------------------------------------------------------------------------------------------
            snapped_start = self.snap_to_mesh_grid(current_start, step, self.mesh)
            if snapped_start is None:
                print(f"Cannot fit the start point to the grid: {current_start}")
                continue
            snapped_end = self.snap_to_mesh_grid(current_end, step, self.mesh)
            if snapped_end is None:
                start_points.insert(0, current_start) # Return the start point to the list because only the end point is invalid
                missed_ends.append(current_end)
                print(f"Cannot fit the end point to the grid: {current_end}")
                continue
            print(f"Start: {current_start} -> {snapped_start}")
            print(f"End: {current_end} -> {snapped_end}")

            path_points = self.a_star(snapped_start, snapped_end, step)

            if path_points:
                # Add original start and end points to the path
                path_points.insert(0, current_start)
                path_points.append(current_end)

                #remove the snapped start and end points
                path_points.pop(1)
                path_points.pop(-2)

                # Add the path points to the occupied set
                for i in range(len(path_points) - 1):
                    self.add_visited(path_points[i], path_points[i + 1])


                # Convert path points to a format suitable for Polyline creation or storage
                self.paths.append(np.array(path_points))
                print(f"Path found")
            else:
                print(f"Missed end point: {current_end}")
                missed_ends.append(current_end)
                start_points.insert(0, current_start)
        return self.paths