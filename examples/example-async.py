#!/usr/bin/env python3

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
Example usage of tev's async Python IPC implementation.
"""

import asyncio

import numpy as np

import tevclient


async def main_async():
    async with tevclient.IpcAsync() as tev_ipc:
        # Create sample image in one go. The image will have RGB channels (displayed as one layer)
        # as well as a 'Bonus' channel (displayed as another layer)
        image_data = np.full((300, 200, 3), 1.0)
        image_data[40:61, :, 0] = 0.0
        image_data[:, 40:61, 1] = 0.0
        image_data[50:71, 50:71, 2] = 0.0

        bonus_data = image_data[:, :, 0] + image_data[:, :, 1] + image_data[:, :, 2]

        await tev_ipc.create_image("Test image 1", width=200, height=300, channel_names=["R", "G", "B", "Bonus"])
        await tev_ipc.update_image("Test image 1", image_data, ["R", "G", "B"])
        await tev_ipc.update_image("Test image 1", bonus_data, ["Bonus"])

        # Create another image that will be populated over time
        RESOLUTION = 256
        TILE_SIZE = 64
        N_TILES = (RESOLUTION // TILE_SIZE) ** 2

        await tev_ipc.create_image("Test image 2", width=RESOLUTION, height=RESOLUTION, channel_names=["R", "G", "B"])

        idx = 0
        for y in range(0, RESOLUTION, TILE_SIZE):
            for x in range(0, RESOLUTION, TILE_SIZE):
                tile = np.full((TILE_SIZE, TILE_SIZE, 3), idx / N_TILES)
                await tev_ipc.update_image("Test image 2", tile, ["R", "G", "B"], x, y)
                await tev_ipc.update_vector_graphics(
                    "Test image 2",
                    [
                        tevclient.vg_begin_path(),
                        tevclient.vg_rect(x, y, TILE_SIZE, TILE_SIZE),
                        # Alternatively: draw rectangle manually
                        # tevclient.vg_move_to(x, y),
                        # tevclient.vg_line_to(x, y + TILE_SIZE),
                        # tevclient.vg_line_to(x + TILE_SIZE, y + TILE_SIZE),
                        # tevclient.vg_line_to(x + TILE_SIZE, y),
                        # tevclient.vg_close_path(),
                        tevclient.vg_stroke(),
                    ],
                )

                idx += 1
                await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main_async())
