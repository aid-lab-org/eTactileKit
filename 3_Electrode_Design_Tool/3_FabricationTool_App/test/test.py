# import pyvista as pv
# import pyacvd

# # 1. Load your mesh (any supported format, e.g. STL/PLY/OBJ)
# original_mesh = pv.read("3_FabricationTool_App/meshes/StanfordBunny.stl")
# # original_mesh = pv.read("3_FabricationTool_App/meshes/Housing_No1.stl")
# # or: original_mesh = pv.read("your_mesh.obj")

# # 2. Initialize clustering
# cluster = pyacvd.Clustering(original_mesh)

# # 3. Optionally, subdivide the mesh internally for more accurate remeshing
# #    This doesn't necessarily directly uniformize the mesh, but it improves
# #    the final distribution of points.
# cluster.subdivide(2).output  # you can adjust the subdivision level

# # 4. Cluster the mesh
# #    You can choose either:
# #       - cluster.cluster(n_points)
# #         specifying the approximate number of points in the resulting mesh
# #       - cluster.cluster(floting value)
# #         specifying the approximate area
# #
# #    For example, to target ~3000 vertices or so:
# cluster.cluster(3000)
# # For example, if you want each triangle to have area ~0.5 mm²
# # target_area = 0.5
# # cluster.cluster(target_area)  # pass a float for approximate area

# # 5. Finally, generate the new, remeshed surface
# remeshed = cluster.create_mesh()

# # 6. (Optional) Save or visualize
# # remeshed.save("your_mesh_remeshed.stl")  # or .ply, .obj, etc.

# # Visualize
# plotter = pv.Plotter()
# plotter.add_mesh(remeshed, show_edges=True)
# plotter.show()


import pyvista as pv
import pyacvd
import numpy as np

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

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
# original_mesh = pv.read("3_FabricationTool_App/meshes/StanfordBunny.stl").triangulate()
original_mesh = pv.read("3_FabricationTool_App/meshes/Housing_No1.stl").triangulate()
mesh_area = original_mesh.area

# Desired average edge length
L_target = 0.5  # in mm

# Initial guess for number of vertices
N_est = estimate_vertex_count(mesh_area, L_target)
print(f"Initial N_est = {N_est} for edge length ~{L_target}")

#subdived the mesh to have a more accurate remeshing
subdivided_mesh = original_mesh.subdivide_adaptive(max_edge_len = 0.2)


max_iterations = 5
tolerance_ratio = 0.05  # +/- 5%
for it in range(max_iterations):
    print(f"\n--- Iteration {it+1} ---")
    print(f"Using N_est = {N_est}")

    # Clustering from the already-subdivided mesh
    acvd = pyacvd.Clustering(subdivided_mesh)
    acvd.cluster(N_est)
    remeshed = acvd.create_mesh()

    # Measure mean edge length
    edge_lengths = compute_edge_lengths(remeshed)
    mean_edge = np.nanmean(edge_lengths) # ignore NaNs
    print(f"Mean edge length = {mean_edge:.4f}")

    # Check convergence
    ratio = mean_edge / L_target
    if abs(ratio - 1.0) < tolerance_ratio:
        print(f"Converged! Mean edge is within +/- {tolerance_ratio*100}% of {L_target}\n")
        break

    # Adjust N_est based on ratio
    # e.g. scale by ratio^2 => #vertices ~ 1 / edge^2
    new_N_est = int(round(N_est * (ratio ** 2)))
    new_N_est = max(new_N_est, 50)  # avoid zero or negative
    print(f"Adjusting N_est from {N_est} -> {new_N_est}")
    N_est = new_N_est

print("\n------------------Done! Checking final stats:------------------")
edge_lengths = compute_edge_lengths(remeshed)
print(f"  Mean edge length:   {edge_lengths.mean():.4f}")
print(f"  Median edge length: {np.median(edge_lengths):.4f}")

# Visualize
p = pv.Plotter()
# p.add_mesh(original_mesh, opacity=0.3, color='white', label='Original')
p.add_mesh(remeshed, show_edges=True, color='tomato', label='Remeshed')
p.add_legend()
p.show()

