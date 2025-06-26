# tevclient
#
# Copyright (C) 2025 Thomas Müller <contact@tom94.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
tevclient

Module for remote-controlling the tev image viewer. This module implements
tev's IPC protocol, allowing you to control tev via a TCP connection. You
can create, modify, reload, and close images as well as overlay vector graphics.
"""

__version__ = "1.0.2"

import socket

from . import packet
from .packet import Tile, VgCommand, Winding


def vg_save():
    return VgCommand(VgCommand.Type.Save)


def vg_restore():
    return VgCommand(VgCommand.Type.Restore)


def vg_fill_color(r: float, g: float, b: float, a: float):
    return VgCommand(VgCommand.Type.FillColor, [r, g, b, a])


def vg_fill():
    return VgCommand(VgCommand.Type.Fill)


def vg_stroke_color(r: float, g: float, b: float, a: float):
    return VgCommand(VgCommand.Type.StrokeColor, [r, g, b, a])


def vg_stroke():
    return VgCommand(VgCommand.Type.Stroke)


def vg_begin_path():
    return VgCommand(VgCommand.Type.BeginPath)


def vg_close_path():
    return VgCommand(VgCommand.Type.ClosePath)


def vg_path_winding(num: int):
    return VgCommand(VgCommand.Type.PathWinding, [float(num)])


def vg_debug_dump_path_cache():
    return VgCommand(VgCommand.Type.DebugDumpPathCache)


def vg_move_to(x: float, y: float):
    return VgCommand(VgCommand.Type.MoveTo, [x, y])


def vg_line_to(x: float, y: float):
    return VgCommand(VgCommand.Type.LineTo, [x, y])


def vg_arc_to(x1: float, y1: float, x2: float, y2: float, radius: float):
    return VgCommand(VgCommand.Type.ArcTo, [x1, y1, x2, y2, radius])


def vg_arc(center_x: float, center_y: float, radius: float, angle_begin: float, angle_end: float, dir: Winding):
    return VgCommand(VgCommand.Type.Arc, [center_x, center_y, radius, angle_begin, angle_end, float(int(dir))])


def vg_bezier_to(c1x: float, c1y: float, c2x: float, c2y: float, x: float, y: float):
    return VgCommand(VgCommand.Type.BezierTo, [c1x, c1y, c2x, c2y, x, y])


def vg_circle(cx: float, cy: float, radius: float):
    return VgCommand(VgCommand.Type.Circle, [cx, cy, radius])


def vg_ellipse(cx: float, cy: float, radius_x: float, radius_y: float):
    return VgCommand(VgCommand.Type.Ellipse, [cx, cy, radius_x, radius_y])


def vg_quad_to(cx: float, cy: float, x: float, y: float):
    return VgCommand(VgCommand.Type.QuadTo, [cx, cy, x, y])


def vg_rect(x: float, y: float, width: float, height: float):
    return VgCommand(VgCommand.Type.Rect, [x, y, width, height])


def vg_rounded_rect(x: float, y: float, width: float, height: float, radius: float):
    return VgCommand(VgCommand.Type.RoundedRect, [x, y, width, height, radius])


def vg_rounded_rect_varying(
    x: float, y: float, width: float, height: float, radius_top_left: float, radius_top_right: float, radius_bottom_right: float, radius_bottom_left: float
):
    return VgCommand(VgCommand.Type.RoundedRectVarying, [x, y, width, height, radius_top_left, radius_top_right, radius_bottom_right, radius_bottom_left])


class IpcAsync:
    def __init__(self, hostname: str = "localhost", port: int = 14158):
        import asyncio

        self._hostname: str = hostname
        self._port: int = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def __aenter__(self):
        import asyncio

        self._reader, self._writer = await asyncio.open_connection(self._hostname, self._port)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        if self._reader is None or self._writer is None:
            raise Exception("Communication was not started")

        self._writer.close()
        await self._writer.wait_closed()

    async def open_image(self, path: str, channel_selector: str = "", grab_focus: bool = True):
        """
        Opens an image from a specified path from the disk of the machine tev is running on.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        self._writer.write(packet.open_image(path, channel_selector, grab_focus))
        await self._writer.drain()

    async def reload_image(self, name: str, grab_focus: bool = True):
        """
        Reloads the image with specified path from the disk of the machine tev is running on.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        self._writer.write(packet.reload_image(name, grab_focus))
        await self._writer.drain()

    async def close_image(self, name: str):
        """
        Closes a specified image.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        self._writer.write(packet.close_image(name))
        await self._writer.drain()

    async def create_image(self, name: str, width: int, height: int, channel_names: list[str] | None = None, grab_focus: bool = True):
        """
        Create a blank image with a specified size and a specified set of channel names. "R", "G", "B" [, "A"] is what should be used if an image is rendered.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        self._writer.write(packet.create_image(name, width, height, channel_names, grab_focus))
        await self._writer.drain()

    async def update_image(
        self,
        name: str,
        image: Tile,
        channel_names: list[str] | None = None,
        x: int = 0,
        y: int = 0,
        grab_focus: bool = False,
        perform_tiling: bool = True,
    ):
        """
        Updates the pixel values of a specified image region and a specified set of channels. The `image` parameter must be laid out in row-major format, i.e.
        from most to least significant: [row][col][channel], where the channel axis is optional.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        if len(image.shape) < 2 or len(image.shape) > 3:
            raise Exception("Image must be 2D or 3D (with channels)")

        # Break down image into tiles of manageable size for typical TCP packets
        tile_size = [128, 128] if perform_tiling else image.shape[0:2]
        for i in range(0, image.shape[0], tile_size[0]):
            for j in range(0, image.shape[1], tile_size[1]):
                tile = image[i : (min(i + tile_size[0], image.shape[0])), j : (min(j + tile_size[1], image.shape[1])), ...]
                data_bytes = packet.update_image(name, tile, channel_names, x + j, y + i, grab_focus)
                self._writer.write(data_bytes)

        await self._writer.drain()

    async def update_vector_graphics(self, name: str, commands: list[VgCommand], append: bool = False, grab_focus: bool = False):
        """
        Draws vector graphics over the specified image. The vector graphics are drawn using an ordered list of commands; see `ipc-example.py` for an example.
        """

        if self._writer is None:
            raise Exception("Communication was not started")

        self._writer.write(packet.update_vector_graphics(name, commands, append, grab_focus))
        await self._writer.drain()


class Ipc:
    def __init__(self, hostname: str = "localhost", port: int = 14158):
        self._hostname: str = hostname
        self._port: int = port
        self._socket: socket.socket | None = None

    def __enter__(self):
        if self._socket is not None:
            raise Exception("Communication already started")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # SOCK_STREAM means TCP
        _ = self._socket.__enter__()
        self._socket.connect((self._hostname, self._port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        if self._socket is None:
            raise Exception("Communication was not started")
        self._socket.__exit__(exc_type, exc_val, exc_tb)  # pyright: ignore[reportUnknownArgumentType]

    def open_image(self, path: str, channel_selector: str = "", grab_focus: bool = True):
        """
        Opens an image from a specified path from the disk of the machine tev is running on.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        self._socket.sendall(packet.open_image(path, channel_selector, grab_focus))

    def reload_image(self, name: str, grab_focus: bool = True):
        """
        Reloads the image with specified path from the disk of the machine tev is running on.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        self._socket.sendall(packet.reload_image(name, grab_focus))

    def close_image(self, name: str):
        """
        Closes a specified image.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        self._socket.sendall(packet.close_image(name))

    def create_image(self, name: str, width: int, height: int, channel_names: list[str] | None = None, grab_focus: bool = True):
        """
        Create a blank image with a specified size and a specified set of channel names. "R", "G", "B" [, "A"] is what should be used if an image is rendered.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        self._socket.sendall(packet.create_image(name, width, height, channel_names, grab_focus))

    def update_image(
        self,
        name: str,
        image: Tile,
        channel_names: list[str] | None = None,
        x: int = 0,
        y: int = 0,
        grab_focus: bool = False,
        perform_tiling: bool = True,
    ):
        """
        Updates the pixel values of a specified image region and a specified set of channels. The `image` parameter must be laid out in row-major format, i.e.
        from most to least significant: [row][col][channel], where the channel axis is optional.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        if len(image.shape) < 2 or len(image.shape) > 3:
            raise Exception("Image must be 2D or 3D (with channels)")

        # Break down image into tiles of manageable size for typical TCP packets
        tile_size = [128, 128] if perform_tiling else image.shape[0:2]
        for i in range(0, image.shape[0], tile_size[0]):
            for j in range(0, image.shape[1], tile_size[1]):
                tile = image[i : (min(i + tile_size[0], image.shape[0])), j : (min(j + tile_size[1], image.shape[1])), ...]
                data_bytes = packet.update_image(name, tile, channel_names, x + j, y + i, grab_focus)
                self._socket.sendall(data_bytes)

    def update_vector_graphics(self, name: str, commands: list[VgCommand], append: bool = False, grab_focus: bool = False):
        """
        Draws vector graphics over the specified image. The vector graphics are drawn using an ordered list of commands; see `ipc-example.py` for an example.
        """

        if self._socket is None:
            raise Exception("Communication was not started")

        self._socket.sendall(packet.update_vector_graphics(name, commands, append, grab_focus))


# `Ipc` used to be called `TevIpc`, so we keep the alias for backwards compatibility.
TevIpc = Ipc
