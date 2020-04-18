import bpy
from bpy.props import (
    FloatProperty, EnumProperty, BoolProperty, PointerProperty
)


class PostFillProperty(bpy.types.PropertyGroup):
    size: FloatProperty(
        name="Size",
        min=0.01,
        max=100.0,
        default=0.05,
        description="Size of each post",
    )

    density: FloatProperty(
        name="Density",
        min=0.0,
        max=1.0,
        default=0.3,
        description="Number of posts along each edge",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "density")
        row.prop(self, "size")


class RailFillProperty(bpy.types.PropertyGroup):
    size: FloatProperty(
        name="Rail Size",
        min=0.01,
        max=100.0,
        default=0.05,
        description="Size of each rail",
    )

    density: FloatProperty(
        name="Rail Density",
        min=0.0,
        max=1.0,
        default=0.3,
        description="Number of rails over each edge",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "density")
        row.prop(self, "size")


class WallFillProperty(bpy.types.PropertyGroup):
    width: FloatProperty(
        name="Wall Width",
        min=0.0,
        max=100.0,
        default=0.075,
        description="Width of each wall",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "width")


class RailProperty(bpy.types.PropertyGroup):

    fill_types = [
        ("POSTS", "Posts", "", 0),
        ("RAILS", "Rails", "", 1),
        ("WALL",  "Wall",  "", 2),
    ]

    fill: EnumProperty(
        name="Fill Type",
        items=fill_types,
        default="POSTS",
        description="Type of railing",
    )

    corner_post_width: FloatProperty(
        name="Width",
        min=0.01,
        max=100.0,
        default=0.1,
        description="Width of each corner post",
    )

    corner_post_height: FloatProperty(
        name="Height",
        min=0.01,
        max=100.0,
        default=0.7,
        description="Height of each corner post",
    )

    has_corner_post: BoolProperty(
        name="Corner Posts",
        default=True,
        description="Whether the railing has corner posts",
    )

    offset: FloatProperty(
        name="Offset",
        default=0.05,
        description="Railings offset",
    )

    post_fill: PointerProperty(type=PostFillProperty)
    rail_fill: PointerProperty(type=RailFillProperty)
    wall_fill: PointerProperty(type=WallFillProperty)

    def draw(self, context, layout):

        row = layout.row()
        row.prop(self, "offset", text="Railing Offset")

        row = layout.row()
        row.prop(self, "fill", text="")

        {
            "POSTS" : self.post_fill,
            "RAILS" : self.rail_fill,
            "WALL"  : self.wall_fill
        }.get(self.fill).draw(context, layout)

        layout.label(text="Corner Posts")
        row = layout.row(align=True)
        row.prop(self, "corner_post_width")
        row.prop(self, "corner_post_height")
