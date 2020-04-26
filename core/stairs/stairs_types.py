import math
import bmesh

from mathutils import Vector, Quaternion
from bmesh.types import BMFace, BMEdge

from ...utils import (
    FaceMap,
    valid_ngon,
    filter_geom,
    popup_message,
    add_faces_to_map,
    create_face,
    local_xyz,
    subdivide_face_vertically,
    subdivide_edges,
    sort_faces,
    sort_edges,
    sort_verts,
    filter_parallel_edges,
    vec_equal,
    extrude_face,
)

from ..railing.railing import create_railing


def create_stairs(bm, faces, prop):
    """Extrude steps from selected faces
    """

    for f in faces:
        f.select = False
        if not valid_ngon(f):
            popup_message("Stairs creation not supported for non-rectangular n-gon!", "Ngon Error")
            return False

        f = create_stairs_split(bm, f, prop)
        add_faces_to_map(bm, [f], FaceMap.STAIRS)

        normal = f.normal.copy()
        top_faces = create_steps(bm, f, prop)

        if prop.has_railing:
            add_railing_to_stairs(bm, top_faces, normal, prop)

        return True


def create_steps(bm, face, prop):
    """ Create stair steps with landing"""
    if prop.landing:
        step_widths = [prop.landing_width] + [prop.step_width] * prop.step_count
    else:
        step_widths = [prop.step_width] * prop.step_count

    if prop.bottom == "FILLED":
        return create_filled_steps(bm, face, step_widths, prop.step_height)
    elif prop.bottom == "BLOCKED":
        return create_blocked_steps(bm, face, step_widths, prop.step_height)
    elif prop.bottom == "SLOPE":
        return create_slope_steps(bm, face, step_widths, prop.step_height)


def create_filled_steps(bm, face, step_widths, step_height):
    """ Create filled stair steps with landing"""

    normal = face.normal.copy()
    top_faces = []

    # create steps
    front_face = face
    for i, step_width in enumerate(step_widths):
        if i == 0:
            front_face, surrounding_faces = extrude_face(bm, front_face, step_width)
            top_faces.append([f for f in surrounding_faces if vec_equal(f.normal, Vector((0., 0., 1.)))][0])
        else:
            bottom_face = list({f for e in front_face.edges for f in e.link_faces if vec_equal(f.normal, Vector((0., 0., -1.)))})[0]
            top_face, front_face, _ = extrude_step(bm, bottom_face, normal, step_height, step_width)
            top_faces.append(top_face)

    return top_faces


def create_blocked_steps(bm, face, step_widths, step_height):
    """ Create blocked steps with landing"""

    normal = face.normal.copy()
    top_faces = []

    # create steps
    front_face = face
    for i, step_width in enumerate(step_widths):
        if i == 0:
            front_face, surrounding_faces = extrude_face(bm, front_face, step_width)
            top_faces.append([f for f in surrounding_faces if vec_equal(f.normal, Vector((0., 0., 1.)))][0])
        else:
            bottom_face = list({f for e in front_face.edges for f in e.link_faces if vec_equal(f.normal, Vector((0., 0., -1.)))})[0]
            edges = filter_parallel_edges(bottom_face.edges, normal)
            widths = [edges[0].calc_length() - step_height, step_height]

            inner_edges = subdivide_edges(bm, edges, normal, widths=widths)
            bottom_face = sort_faces(list({f for e in inner_edges for f in e.link_faces}), normal)[1]

            top_face, front_face, _ = extrude_step(bm, bottom_face, normal, step_height, step_width)
            top_faces.append(top_face)

    return top_faces


def create_slope_steps(bm, face, step_widths, step_height):
    """ Create slope steps with landing"""

    normal = face.normal.copy()
    top_faces = []

    # create steps
    front_face = face
    for i, step_width in enumerate(step_widths):
        if i == 0:
            front_face, surrounding_faces = extrude_face(bm, front_face, step_width)
            top_faces.append([f for f in surrounding_faces if vec_equal(f.normal, Vector((0., 0., 1.)))][0])
        else:
            bottom_face = list({f for e in front_face.edges for f in e.link_faces if vec_equal(f.normal, Vector((0., 0., -1.)))})[0]

            e1 = sort_edges(bottom_face.edges, normal)[0]
            edges = filter_parallel_edges(bottom_face.edges, normal)
            widths = [edges[0].calc_length() - step_height, step_height]
            inner_edges = subdivide_edges(bm, edges, normal, widths=widths)
            bottom_face = sort_faces(list({f for e in inner_edges for f in e.link_faces}), normal)[1]
            e2 = sort_edges(bottom_face.edges, normal)[0]

            top_face, front_face, _ = extrude_step(bm, bottom_face, normal, step_height, step_width)
            top_faces.append(top_face)

            bmesh.ops.translate(bm, verts=e2.verts, vec=-2*normal*step_width/2)
            bmesh.ops.remove_doubles(bm, verts=list(e1.verts)+list(e2.verts), dist=0.001)

    return top_faces


def extrude_step(bm, face, normal, step_height, step_width):
    """ Extrude a stair step from previous bottom face
    """
    # extrude down
    n = face.normal.copy()
    face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[0]
    bmesh.ops.translate(bm, vec=n*step_height, verts=face.verts)

    # extrude front
    front_face = list({f for e in face.edges for f in e.link_faces if vec_equal(f.normal, normal)})[0]
    front_face, surrounding_faces = extrude_face(bm, front_face, step_width)
    flat_edges = list({e for f in surrounding_faces for e in f.edges if e.calc_face_angle() < 0.001 and e.calc_face_angle() > -0.001})
    bmesh.ops.dissolve_edges(bm, edges=flat_edges, use_verts=True)
    top_face = list({f for e in front_face.edges for f in e.link_faces if vec_equal(f.normal, Vector((0., 0., 1.)))})[0]
    bottom_face = list({f for e in front_face.edges for f in e.link_faces if vec_equal(f.normal, Vector((0., 0., -1.)))})[0]

    return top_face, front_face, bottom_face


def subdivide_next_step(bm, ret_face, remaining, step_height):
    """ cut the next face step height
    """
    return subdivide_face_vertically(bm, ret_face, widths=[remaining*step_height, step_height])[0]


def create_stairs_split(bm, face, prop):
    """Use properties to create face
    """
    xyz = local_xyz(face)
    size = Vector((prop.size_offset.size.x, prop.step_height))
    f = create_face(bm, size, prop.size_offset.offset, xyz)
    bmesh.ops.translate(
        bm, verts=f.verts, vec=face.calc_center_bounds() - face.normal*prop.depth_offset
    )
    if not vec_equal(f.normal, face.normal):
        bmesh.ops.reverse_faces(bm, faces=[f])
    return f


def add_railing_to_stairs(bm, top_faces, normal, prop):
    steps = sort_faces(top_faces, normal)
    first_step = steps[0]
    last_step = steps[-1]

    # create railing initial edges
    if prop.landing:
        v1, v2 = railing_verts(bm, sort_verts(first_step.verts, normal)[:2], normal, prop.rail.offset, prop.rail.corner_post_width/2)
        v3, v4 = railing_verts(bm, sort_verts(first_step.verts, normal)[-2:], normal, prop.rail.offset, -prop.step_width/2)
        v5, v6 = railing_verts(bm, sort_verts(last_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        e1 = bmesh.ops.contextual_create(bm, geom=(v1, v3))["edges"][0]
        e2 = bmesh.ops.contextual_create(bm, geom=[v3, v5])["edges"][0]
        e3 = bmesh.ops.contextual_create(bm, geom=[v2, v4])["edges"][0]
        e4 = bmesh.ops.contextual_create(bm, geom=[v4, v6])["edges"][0]
        railing_edges = [e1, e2, e3, e4]
    else:
        v1, v2 = railing_verts(bm, sort_verts(first_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        v3, v4 = railing_verts(bm, sort_verts(last_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        e1 = bmesh.ops.contextual_create(bm, geom=(v1, v3))["edges"][0]
        e2 = bmesh.ops.contextual_create(bm, geom=[v2, v4])["edges"][0]
        railing_edges = [e1, e2]

    # extrude edges
    ret = bmesh.ops.extrude_edge_only(bm, edges=railing_edges)
    top_edges = filter_geom(ret["geom"], BMEdge)
    top_verts = list({v for e in top_edges for v in e.verts})
    bmesh.ops.translate(bm, verts=top_verts, vec=Vector((0., 0., 1.))*prop.rail.corner_post_height)
    railing_faces = filter_geom(ret["geom"], BMFace)

    create_railing(bm, railing_faces, prop.rail, normal)


def railing_verts(bm, verts, normal, offset, depth):
    tangent = normal.copy()
    tangent.rotate(Quaternion(Vector((0., 0., 1.)), math.pi/2).to_euler())
    verts = sort_verts(verts, tangent)
    co1 = verts[0].co + depth * normal
    co2 = verts[1].co + depth * normal
    v1 = bmesh.ops.create_vert(bm, co=co1)["vert"][0]
    v2 = bmesh.ops.create_vert(bm, co=co2)["vert"][0]
    bmesh.ops.translate(bm, verts=[v1], vec=tangent*offset)
    bmesh.ops.translate(bm, verts=[v2], vec=-tangent*offset)
    return v1, v2
