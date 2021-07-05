from struct import unpack, pack

from game.world.managers.maps.MapManager import MapManager
from database.realm.RealmDatabaseManager import RealmDatabaseManager
from network.packet.PacketWriter import PacketWriter, OpCode
from utils import Formulas
from utils.constants.MiscCodes import HighGuid


class BinderActivateHandler(object):

    @staticmethod
    def handle(world_session, socket, reader):
        if len(reader.data) >= 8:  # Avoid handling empty binder activate packet.
            binder_guid = unpack('<Q', reader.data[:8])[0]
            binder = MapManager.get_surrounding_unit_by_guid(world_session.player_mgr, binder_guid)
            if not binder or binder.location.distance(world_session.player_mgr.location) > Formulas.Distances.MAX_BIND_DISTANCE:
                return 0

            if binder.location.distance(x=world_session.player_mgr.deathbind.deathbind_position_x,
                                        y=world_session.player_mgr.deathbind.deathbind_position_y,
                                        z=world_session.player_mgr.deathbind.deathbind_position_z)\
                    < Formulas.Distances.MAX_BIND_RADIUS_CHECK:
                world_session.enqueue_packet(PacketWriter.get_packet(OpCode.SMSG_PLAYERBINDERROR))
            else:
                world_session.player_mgr.deathbind.creature_binder_guid = binder_guid & ~HighGuid.HIGHGUID_UNIT
                world_session.player_mgr.deathbind.deathbind_map = world_session.player_mgr.map_
                world_session.player_mgr.deathbind.deathbind_zone = world_session.player_mgr.zone
                world_session.player_mgr.deathbind.deathbind_position_x = world_session.player_mgr.location.x
                world_session.player_mgr.deathbind.deathbind_position_y = world_session.player_mgr.location.y
                world_session.player_mgr.deathbind.deathbind_position_z = world_session.player_mgr.location.z
                RealmDatabaseManager.character_update_deathbind(world_session.player_mgr.deathbind)
                world_session.enqueue_packet(world_session.player_mgr.get_deathbind_packet())

                data = pack('<Q', binder_guid)
                world_session.enqueue_packet(PacketWriter.get_packet(OpCode.SMSG_PLAYERBOUND, data))

        return 0
