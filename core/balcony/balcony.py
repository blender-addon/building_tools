import bpy
import bmesh

from .balcony_types import make_balcony
from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )

class Balcony:

    @classmethod
    def build(cls, context, props):
        """Use balcony types and properties to generate geomerty

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): BalconyProperty
        """

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(bm, faces):
            make_balcony(bm, faces, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, bm, faces):
        """ Ensure user has appropriate selection if any """
        if faces:
            # -- ensure all are upward facing
            if all([f.normal.z == 1.0 for f in faces]):
                return True
        return False
