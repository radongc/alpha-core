from game.world.managers.CommandManager import CommandManager

from network.packet.PacketReader import *


class CreateItemHandler(object):

    @staticmethod
    def handle(world_session, socket, reader: PacketReader) -> int:
        if len(reader.data) >= 4:  # Avoid handling empty create item packet.
            if not world_session.player_mgr.is_gm:
                return 0

            item_entry = unpack('<I', reader.data[:4])[0]
            CommandManager.additem(world_session, str(item_entry))

        return 0
