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

import struct
from enum import IntEnum

import numpy as np

GrayscaleTile = np.ndarray[tuple[int, int], np.dtype[np.float32]]
ColoredTile = np.ndarray[tuple[int, int, int], np.dtype[np.float32]]
Tile = GrayscaleTile | ColoredTile


class Winding(IntEnum):
    CounterClockwise = 1
    Clockwise = 2


class VgCommand:
    class Type(IntEnum):
        # This stays in sync with `VgCommand::EType` from VectorGraphics.h
        Save = 0
        Restore = 1
        FillColor = 2
        Fill = 3
        StrokeColor = 4
        Stroke = 5
        BeginPath = 6
        ClosePath = 7
        PathWinding = 8
        DebugDumpPathCache = 9
        MoveTo = 10
        LineTo = 11
        ArcTo = 12
        Arc = 13
        BezierTo = 14
        Circle = 15
        Ellipse = 16
        QuadTo = 17
        Rect = 18
        RoundedRect = 19
        RoundedRectVarying = 20

    def __init__(self, type: Type, data: list[float] | None = None):
        self.type: VgCommand.Type = type
        self.data: list[float] | None = data


class IpcPacketType(IntEnum):
    # This stays in sync with `IpcPacket::EType` from Ipc.h
    OpenImage = 7  # v2
    ReloadImage = 1
    CloseImage = 2
    CreateImage = 4
    UpdateImage = 6  # v3
    VectorGraphics = 8


def open_image(path: str, channel_selector: str = "", grab_focus: bool = True) -> bytearray:
    """
    Opens an image from a specified path from the disk of the machine tev is running on.
    """

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.OpenImage))
    data_bytes.extend(struct.pack("<b", grab_focus))
    data_bytes.extend(bytes(path, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator
    data_bytes.extend(bytes(channel_selector, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes


def reload_image(name: str, grab_focus: bool = True) -> bytearray:
    """
    Reloads the image with specified path from the disk of the machine tev is running on.
    """

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.ReloadImage))
    data_bytes.extend(struct.pack("<b", grab_focus))
    data_bytes.extend(bytes(name, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes


def close_image(name: str) -> bytearray:
    """
    Closes a specified image.
    """

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.CloseImage))
    data_bytes.extend(bytes(name, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes


def create_image(name: str, width: int, height: int, channel_names: list[str] | None = None, grab_focus: bool = True) -> bytearray:
    """
    Create a blank image with a specified size and a specified set of channel names. "R", "G", "B" [, "A"] is what should be used if an image is rendered.
    """

    if channel_names is None:
        channel_names = ["R", "G", "B", "A"]

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.CreateImage))
    data_bytes.extend(struct.pack("<b", grab_focus))
    data_bytes.extend(bytes(name, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator
    data_bytes.extend(struct.pack("<i", width))
    data_bytes.extend(struct.pack("<i", height))
    data_bytes.extend(struct.pack("<i", len(channel_names)))
    for channel_name in channel_names:
        data_bytes.extend(bytes(channel_name, "ascii"))
        data_bytes.extend(struct.pack("<b", 0))  # string terminator

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes


def update_image(name: str, image: Tile, channel_names: list[str] | None = None, x: int = 0, y: int = 0, grab_focus: bool = False) -> bytearray:
    """
    Updates the pixel values of a specified image region and a specified set of channels. The `image` parameter must be laid out in row-major format, i.e.
    from most to least significant: [row][col][channel], where the channel axis is optional.
    """

    if len(image.shape) < 2 or len(image.shape) > 3:
        raise Exception("Image must be 2D or 3D (with channels)")

    if channel_names is None:
        channel_names = ["R", "G", "B", "A"]

    n_channels = 1 if len(image.shape) < 3 else image.shape[2]

    channel_offsets = [i for i in range(n_channels)]
    channel_strides = [n_channels for _ in range(n_channels)]

    if len(channel_names) < n_channels:
        raise Exception("Not enough channel names provided")

    tile_dense = np.full_like(image, 0.0, dtype="<f")
    tile_dense[...] = image[...]

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.UpdateImage))
    data_bytes.extend(struct.pack("<b", grab_focus))
    data_bytes.extend(bytes(name, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator
    data_bytes.extend(struct.pack("<i", n_channels))

    for channel_name in channel_names[0:n_channels]:
        data_bytes.extend(bytes(channel_name, "UTF-8"))
        data_bytes.extend(struct.pack("<b", 0))  # string terminator

    data_bytes.extend(struct.pack("<i", x))  # x
    data_bytes.extend(struct.pack("<i", y))  # y
    data_bytes.extend(struct.pack("<i", tile_dense.shape[1]))  # width
    data_bytes.extend(struct.pack("<i", tile_dense.shape[0]))  # height

    for channel_offset in channel_offsets:
        data_bytes.extend(struct.pack("<q", channel_offset))
    for channel_stride in channel_strides:
        data_bytes.extend(struct.pack("<q", channel_stride))

    data_bytes.extend(tile_dense.tobytes())  # data

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes


def update_vector_graphics(name: str, commands: list[VgCommand], append: bool = False, grab_focus: bool = False) -> bytearray:
    """
    Draws vector graphics over the specified image. The vector graphics are drawn using an ordered list of commands; see `ipc-example.py` for an example.
    """

    data_bytes = bytearray()
    data_bytes.extend(struct.pack("<I", 0))  # reserved for length
    data_bytes.extend(struct.pack("<b", IpcPacketType.VectorGraphics))
    data_bytes.extend(struct.pack("<b", grab_focus))
    data_bytes.extend(bytes(name, "UTF-8"))
    data_bytes.extend(struct.pack("<b", 0))  # string terminator
    data_bytes.extend(struct.pack("<b", append))
    data_bytes.extend(struct.pack("<I", len(commands)))
    for command in commands:
        data_bytes.extend(struct.pack("<b", command.type))
        if command.data is not None:
            data_bytes.extend(np.array(command.data, dtype="<f").tobytes())

    data_bytes[0:4] = struct.pack("<I", len(data_bytes))
    return data_bytes
