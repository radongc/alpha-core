import traceback

from database.dbc.DbcDatabaseManager import DbcDatabaseManager
from game.world.managers.maps.AreaInformation import AreaInformation
from game.world.managers.maps.Constants import SIZE, RESOLUTION_ZMAP, RESOLUTION_AREA_INFO
from game.world.managers.maps.Map import Map
from game.world.managers.maps.MapTile import MapTile
from utils.ConfigManager import config
from utils.Logger import Logger

MAPS = {}
MAP_LIST = DbcDatabaseManager.map_get_all_ids()
AREAS = {}
AREA_LIST = DbcDatabaseManager.area_get_all_ids()


class MapManager(object):
    @staticmethod
    def initialize_maps():
        for map_id in MAP_LIST:
            MAPS[map_id] = Map(map_id, MapManager.on_cell_turn_active)

    @staticmethod
    def initialize_area_tables():
        for area_id in AREA_LIST:
            AREAS[area_id] = DbcDatabaseManager.area_get_by_id(area_id)

    @staticmethod
    def get_area_number_by_zone_id(zone_id):
        if zone_id in AREAS:
            return AREAS[zone_id].AreaNumber
        return zone_id

    @staticmethod
    def get_parent_zone_id(zone_id, map_id):
        if zone_id in AREAS and AREAS[zone_id].ParentAreaNum > 0:
            parent = DbcDatabaseManager.area_get_by_area_number(AREAS[zone_id].ParentAreaNum, map_id)
            if parent:
                return parent.ID
        return zone_id

    @staticmethod
    def on_cell_turn_active(world_object):
        MapManager.load_map_tiles(world_object.map_, world_object.location.x, world_object.location.y)

    @staticmethod
    def load_map_tiles(map_id, x, y):
        if not config.Server.Settings.use_map_tiles:
            return

        if map_id not in MAP_LIST:
            return

        x = MapManager.get_tile_x(x)
        y = MapManager.get_tile_y(y)

        for i in range(-1, 1):
            for j in range(-1, 1):
                if -1 < x + i < 64 and -1 < y + j < 64:
                    # Avoid loading tiles information if we already did.
                    if not MAPS[map_id].tiles_used[x + i][y + j]:
                        MAPS[map_id].tiles_used[x + i][y + j] = True
                        MAPS[map_id].tiles[x + i][y + j] = MapTile(map_id, x + i, y + j)

    @staticmethod
    def get_tile(x, y):
        tile_x = int(32.0 - MapManager.validate_map_coord(x) / SIZE)
        tile_y = int(32.0 - MapManager.validate_map_coord(y) / SIZE)
        return [tile_x, tile_y]

    @staticmethod
    def get_tile_x(x):
        tile_x = int(32.0 - MapManager.validate_map_coord(x) / SIZE)
        return tile_x

    @staticmethod
    def get_tile_y(y):
        tile_y = int(32.0 - MapManager.validate_map_coord(y) / SIZE)
        return tile_y

    @staticmethod
    def get_submap_tile_x(x):
        tile_x = int((RESOLUTION_ZMAP - 1) * (
                32.0 - MapManager.validate_map_coord(x) / SIZE - int(32.0 - MapManager.validate_map_coord(x) / SIZE)))

        return tile_x

    @staticmethod
    def get_submap_tile_y(y):
        tile_y = int((RESOLUTION_ZMAP - 1) * (
                32.0 - MapManager.validate_map_coord(y) / SIZE - int(32.0 - MapManager.validate_map_coord(y) / SIZE)))

        return tile_y

    @staticmethod
    def calculate_z_for_object(world_object):
        return MapManager.calculate_z(world_object.map_, world_object.location.x, world_object.location.y,
                                      world_object.location.z)

    @staticmethod
    def calculate_z(map_id, x, y, current_z=0.0):
        try:
            map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, (RESOLUTION_ZMAP - 1))
            x_normalized = (RESOLUTION_ZMAP - 1) * (32.0 - (x / SIZE) - map_tile_x) - tile_local_x
            y_normalized = (RESOLUTION_ZMAP - 1) * (32.0 - (y / SIZE) - map_tile_y) - tile_local_y

            if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
                Logger.warning(f'Tile [{map_tile_x},{map_tile_y}] information not found.')
                return current_z if current_z else 0.0
            else:
                try:
                    val_1 = MapManager.get_height(map_id, map_tile_x, map_tile_y, tile_local_x, tile_local_y)
                    val_2 = MapManager.get_height(map_id, map_tile_x, map_tile_y, tile_local_x + 1, tile_local_y)
                    top_height = MapManager._lerp(val_1, val_2, x_normalized)
                    val_3 = MapManager.get_height(map_id, map_tile_x, map_tile_y, tile_local_x, tile_local_y + 1)
                    val_4 = MapManager.get_height(map_id, map_tile_x, map_tile_y, tile_local_x + 1, tile_local_y + 1)
                    bottom_height = MapManager._lerp(val_3, val_4, x_normalized)
                    return MapManager._lerp(top_height, bottom_height, y_normalized)  # Z
                except:
                    return MAPS[map_id].tiles[map_tile_x][map_tile_y].z_coords[tile_local_x][tile_local_x]
        except:
            Logger.error(traceback.format_exc())
            return current_z if current_z else 0.0

    @staticmethod
    def get_area_information(world_object):
        map_id = world_object.map_
        x = world_object.location.x
        y = world_object.location.y
        area_number = MapManager.get_area_number(map_id, x, y)
        area_table = DbcDatabaseManager.area_get_by_area_number(area_number, map_id)
        area_name = area_table.AreaName_enUS
        area_flags = MapManager.get_area_flags(map_id, x, y)
        area_level = MapManager.get_area_level(map_id, x, y)
        area_explore_bit = MapManager.get_area_explore_flag(map_id, x, y)
        area_faction_mask = MapManager.get_area_faction_mask(map_id, x, y)

        # If unable to retrieve any of the area information, return None.
        if area_number < 0 or area_flags < 0 or area_level < 0 or area_explore_bit < 0 or area_faction_mask < 0:
            return None
        return AreaInformation(area_table.ID, area_number, area_name, area_flags, area_level, area_explore_bit, area_faction_mask)

    @staticmethod
    def get_area_number(map_id, x, y):
        map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_AREA_INFO - 1)
        if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
            return -1
        return MAPS[map_id].tiles[map_tile_x][map_tile_y].area_number[tile_local_x][tile_local_y]

    @staticmethod
    def get_area_flags(map_id, x, y):
        map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_AREA_INFO - 1)
        if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
            return -1
        return MAPS[map_id].tiles[map_tile_x][map_tile_y].area_flags[tile_local_x][tile_local_y]

    @staticmethod
    def get_area_level(map_id, x, y):
        map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_AREA_INFO - 1)
        if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
            return -1
        return MAPS[map_id].tiles[map_tile_x][map_tile_y].area_level[tile_local_x][tile_local_y]

    @staticmethod
    def get_area_explore_flag(map_id, x, y):
        map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_AREA_INFO - 1)
        if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
            return -1
        return MAPS[map_id].tiles[map_tile_x][map_tile_y].area_explore_flag[tile_local_x][tile_local_y]

    @staticmethod
    def get_area_faction_mask(map_id, x, y):
        map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_AREA_INFO - 1)
        if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
            return -1
        return MAPS[map_id].tiles[map_tile_x][map_tile_y].area_faction_mask[tile_local_x][tile_local_y]

    @staticmethod
    def get_water_level(map_id, x, y):
        return 0.0  # TODO
        # map_tile_x, map_tile_y, tile_local_x, tile_local_y = MapManager.calculate_tile(x, y, RESOLUTION_WATER)
        # if map_id not in MAPS or not MAPS[map_id].tiles[map_tile_x][map_tile_y]:
        #     return 0.0
        # return MAPS[map_id].tiles[map_tile_x][map_tile_y].water_level[tile_local_x][tile_local_y]

    @staticmethod
    def calculate_tile(x, y, resolution):
        x = MapManager.validate_map_coord(x)
        y = MapManager.validate_map_coord(y)
        map_tile_x = int(32.0 - (x / SIZE))
        map_tile_y = int(32.0 - (y / SIZE))
        tile_local_x = int(resolution * (32.0 - (x / SIZE) - map_tile_x))
        tile_local_y = int(resolution * (32.0 - (y / SIZE) - map_tile_y))
        return map_tile_x, map_tile_y, tile_local_x, tile_local_y

    @staticmethod
    def get_height(map_id, map_tile_x, map_tile_y, map_tile_local_x, map_tile_local_y):
        if map_tile_local_x > RESOLUTION_ZMAP:
            map_tile_x = int(map_tile_x + 1)
            map_tile_local_x = int(map_tile_local_x - RESOLUTION_ZMAP)
        elif map_tile_local_x < 0:
            map_tile_x = int(map_tile_x - 1)
            map_tile_local_x = int(-map_tile_local_x - 1)

        if map_tile_local_y > RESOLUTION_ZMAP:
            map_tile_y = int(map_tile_y + 1)
            map_tile_local_y = int(map_tile_local_y - RESOLUTION_ZMAP)
        elif map_tile_local_y < 0:
            map_tile_y = int(map_tile_y - 1)
            map_tile_local_y = int(-map_tile_local_y - 1)

        return MAPS[map_id].tiles[map_tile_x][map_tile_y].z_coords[map_tile_local_x][map_tile_local_y]

    @staticmethod
    def validate_map_coord(coord):
        if coord > 32.0 * SIZE:
            return 32.0 * SIZE
        elif coord < -32.0 * SIZE:
            return -32 * SIZE
        else:
            return coord

    @staticmethod
    def get_grid_manager_by_map_id(map_id):
        if map_id in MAPS:
            return MAPS[map_id].grid_manager
        return None

    @staticmethod
    def _lerp(value1, value2, amount):
        return value1 + (value2 - value1) * amount

    # Object methods (wrappers around GridManager methods)

    @staticmethod
    def should_relocate(world_object, destination, destination_map):
        grid_manager = MapManager.get_grid_manager_by_map_id(destination_map)
        destination_cells = grid_manager.get_surrounding_cells_by_location(destination.x, destination.y, destination_map)
        current_cell = grid_manager.get_cells()[world_object.current_cell]
        return current_cell in destination_cells

    @staticmethod
    def update_object(world_object):
        grid_manager = MapManager.get_grid_manager_by_map_id(world_object.map_)
        grid_manager.update_object(world_object)

    @staticmethod
    def remove_object(world_object):
        MapManager.get_grid_manager_by_map_id(world_object.map_).remove_object(world_object)

    @staticmethod
    def send_surrounding(packet, world_object, include_self=True, exclude=None, use_ignore=False):
        MapManager.get_grid_manager_by_map_id(world_object.map_).send_surrounding(
            packet, world_object, include_self, exclude, use_ignore)

    @staticmethod
    def send_surrounding_in_range(packet, world_object, range_, include_self=True, exclude=None, use_ignore=False):
        MapManager.get_grid_manager_by_map_id(world_object.map_).send_surrounding_in_range(
            packet, world_object, range_, include_self, exclude, use_ignore)

    @staticmethod
    def get_surrounding_objects(world_object, object_types):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_objects(world_object, object_types)

    @staticmethod
    def get_surrounding_players(world_object):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_players(world_object)

    @staticmethod
    def get_surrounding_units(world_object, include_players=False):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_units(world_object, include_players)

    @staticmethod
    def get_surrounding_units_by_location(vector, target_map, range_, include_players=False):
        grid_mgr = MapManager.get_grid_manager_by_map_id(target_map)
        if not grid_mgr:
            return [{}, {}]
        return grid_mgr.get_surrounding_units_by_location(vector, target_map, range_, include_players)

    @staticmethod
    def get_surrounding_gameobjects(world_object):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_gameobjects(world_object)

    @staticmethod
    def get_surrounding_player_by_guid(world_object, guid):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_player_by_guid(world_object, guid)

    @staticmethod
    def get_surrounding_unit_by_guid(world_object, guid, include_players=False):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_unit_by_guid(world_object, guid, include_players)

    @staticmethod
    def get_surrounding_gameobject_by_guid(world_object, guid):
        return MapManager.get_grid_manager_by_map_id(world_object.map_).get_surrounding_gameobject_by_guid(world_object, guid)

    @staticmethod
    def update_creatures():
        for map_id, map_ in MAPS.items():
            map_.grid_manager.update_creatures()

    @staticmethod
    def update_gameobjects():
        for map_id, map_ in MAPS.items():
            map_.grid_manager.update_gameobjects()

    @staticmethod
    def deactivate_cells():
        for map_id, map_ in MAPS.items():
            map_.grid_manager.deactivate_cells()
