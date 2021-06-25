import os
from typing import Optional
from difflib import SequenceMatcher

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database.world.WorldModels import *
from utils.ConfigManager import *
from utils.constants.MiscCodes import HighGuid

DB_USER = os.getenv('MYSQL_USERNAME', config.Database.Connection.username)
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', config.Database.Connection.password)
DB_HOST = os.getenv('MYSQL_HOST', config.Database.Connection.host)
DB_WORLD_NAME = config.Database.DBNames.world_db

world_db_engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_WORLD_NAME}?charset=utf8mb4',
                                pool_pre_ping=True)
SessionHolder = scoped_session(sessionmaker(bind=world_db_engine, autocommit=True, autoflush=True))


class WorldDatabaseManager(object):
    # Player stuff

    @staticmethod
    def player_create_info_get(race, class_):
        world_db_session = SessionHolder()
        res = world_db_session.query(Playercreateinfo).filter_by(race=race, _class=class_).first()
        world_db_session.close()
        return res

    @staticmethod
    def player_create_spell_get(race, class_):
        world_db_session = SessionHolder()
        res = world_db_session.query(PlayercreateinfoSpell).filter_by(race=race, _class=class_).all()
        world_db_session.close()
        return res

    @staticmethod
    def player_create_item_get(race, class_):
        world_db_session = SessionHolder()
        res = world_db_session.query(PlayercreateinfoItem).filter_by(race=race, _class=class_).all()
        world_db_session.close()
        return res

    @staticmethod
    def player_get_class_level_stats(class_, level):
        world_db_session = SessionHolder()
        res = world_db_session.query(PlayerClasslevelstats).filter_by(level=level, _class=class_).first()
        world_db_session.close()
        return res

    @staticmethod
    def player_get_level_stats(class_, level, race):
        world_db_session = SessionHolder()
        res = world_db_session.query(PlayerLevelstats).filter_by(level=level, _class=class_, race=race).first()
        world_db_session.close()
        return res

    # Area trigger stuff

    @staticmethod
    def area_trigger_teleport_get_by_id(trigger_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(AreatriggerTeleport).filter_by(id=trigger_id).first()
        world_db_session.close()
        return res

    # Area Template stuff

    @staticmethod
    def area_get_by_id(area_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(AreaTemplate).filter_by(entry=area_id).first()
        world_db_session.close()
        return res

    @staticmethod
    def area_get_by_explore_flags(explore_flags, map_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(AreaTemplate).filter_by(explore_flag=explore_flags, map_id=map_id).first()
        world_db_session.close()
        return res

    # Worldport stuff

    @staticmethod
    def worldport_get_by_name(name, return_all=False):
        world_db_session = SessionHolder()
        best_matching_location = None
        best_matching_ratio = 0
        locations = world_db_session.query(Worldports).filter(Worldports.name.like('%' + name + '%')).all()
        world_db_session.close()

        if return_all:
            return locations

        for location in locations:
            ratio = SequenceMatcher(None, location.name.lower(), name.lower()).ratio()
            if ratio > best_matching_ratio:
                best_matching_ratio = ratio
                best_matching_location = location
        return best_matching_location

    # Item stuff

    class ItemTemplateHolder:
        ITEM_TEMPLATES = {}

        @staticmethod
        def load_item_template(item_template):
            WorldDatabaseManager.ItemTemplateHolder.ITEM_TEMPLATES[item_template.entry] = item_template

        @staticmethod
        def item_template_get_by_entry(entry):
            if entry in WorldDatabaseManager.ItemTemplateHolder.ITEM_TEMPLATES:
                return WorldDatabaseManager.ItemTemplateHolder.ITEM_TEMPLATES[entry]
            return None

    @staticmethod
    def item_template_get_all():
        world_db_session = SessionHolder()
        res = world_db_session.query(ItemTemplate).filter_by().all()
        world_db_session.close()
        return res

    @staticmethod
    def item_template_get_by_name(name, return_all=False):
        world_db_session = SessionHolder()
        best_matching_item = None
        best_matching_ratio = 0
        items = world_db_session.query(ItemTemplate).filter(ItemTemplate.name.like('%' + name + '%')).all()
        world_db_session.close()

        if return_all:
            return items

        for item in items:
            ratio = SequenceMatcher(None, item.name.lower(), name.lower()).ratio()
            if ratio > best_matching_ratio:
                best_matching_ratio = ratio
                best_matching_item = item
        return best_matching_item

    # Page text stuff

    @staticmethod
    def page_text_get_by_id(page_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(PageText).filter_by(entry=page_id).first()
        world_db_session.close()
        return res

    # Gameobject stuff

    @staticmethod
    def gameobject_get_all_spawns():
        world_db_session = SessionHolder()
        res = world_db_session.query(SpawnsGameobjects).filter_by(ignored=0).all()
        return res, world_db_session

    @staticmethod
    def gameobject_spawn_get_by_guid(guid):
        world_db_session = SessionHolder()
        res = world_db_session.query(SpawnsGameobjects).filter_by(spawn_id=guid & ~HighGuid.HIGHGUID_GAMEOBJECT).first()
        return res, world_db_session

    @staticmethod
    def gameobject_template_get_by_entry(entry):
        world_db_session = SessionHolder()
        res = world_db_session.query(GameobjectTemplate).filter_by(entry=entry).first()
        return res, world_db_session

    @staticmethod
    def gameobject_get_loot_template():
        world_db_session = SessionHolder()
        res = world_db_session.query(GameobjectLootTemplate).all()
        world_db_session.close()
        return res

    class GameObjectLootTemplateHolder:
        GAMEOBJECT_LOOT_TEMPLATES = {}

        @staticmethod
        def load_gameobject_loot_template(gameobject_template):
            if gameobject_template.entry not in WorldDatabaseManager.GameObjectLootTemplateHolder.GAMEOBJECT_LOOT_TEMPLATES:
                WorldDatabaseManager.GameObjectLootTemplateHolder.GAMEOBJECT_LOOT_TEMPLATES[gameobject_template.entry] = []

            WorldDatabaseManager.GameObjectLootTemplateHolder.GAMEOBJECT_LOOT_TEMPLATES[gameobject_template.entry]\
                .append(gameobject_template)

        @staticmethod
        def gameobject_loot_template_get_by_entry(entry):
            return WorldDatabaseManager.GameObjectLootTemplateHolder.GAMEOBJECT_LOOT_TEMPLATES[entry]\
                if entry in WorldDatabaseManager.GameObjectLootTemplateHolder.GAMEOBJECT_LOOT_TEMPLATES else []

    # Creature stuff

    @staticmethod
    def creature_get_by_entry(entry):
        world_db_session = SessionHolder()
        res = world_db_session.query(CreatureTemplate).filter_by(entry=entry).first()
        world_db_session.close()
        return res

    @staticmethod
    def creature_get_all_spawns():
        world_db_session = SessionHolder()
        res = world_db_session.query(SpawnsCreatures).filter_by(ignored=0).all()
        return res, world_db_session

    @staticmethod
    def creature_spawn_get_by_guid(guid):
        world_db_session = SessionHolder()
        res = world_db_session.query(SpawnsCreatures).filter_by(spawn_id=guid & ~HighGuid.HIGHGUID_UNIT).first()
        return res, world_db_session

    @staticmethod
    def creature_get_model_info(display_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(CreatureModelInfo).filter_by(modelid=display_id).first()
        world_db_session.close()
        return res

    class CreatureLootTemplateHolder:
        CREATURE_LOOT_TEMPLATES = {}

        @staticmethod
        def load_creature_loot_template(creature_loot_template):
            if creature_loot_template.entry not in WorldDatabaseManager.CreatureLootTemplateHolder.CREATURE_LOOT_TEMPLATES:
                WorldDatabaseManager.CreatureLootTemplateHolder.CREATURE_LOOT_TEMPLATES[creature_loot_template.entry] = []

            WorldDatabaseManager.CreatureLootTemplateHolder.CREATURE_LOOT_TEMPLATES[creature_loot_template.entry]\
                .append(creature_loot_template)

        @staticmethod
        def creature_loot_template_get_by_creature(creature_entry):
            return WorldDatabaseManager.CreatureLootTemplateHolder.CREATURE_LOOT_TEMPLATES[creature_entry] \
                if creature_entry in WorldDatabaseManager.CreatureLootTemplateHolder.CREATURE_LOOT_TEMPLATES else []

    @staticmethod
    def creature_get_loot_template():
        world_db_session = SessionHolder()
        res = world_db_session.query(CreatureLootTemplate).all()
        world_db_session.close()
        return res

    @staticmethod
    def creature_get_vendor_data(entry):
        world_db_session = SessionHolder()
        res = world_db_session.query(NpcVendor).filter_by(entry=entry).all()
        return res, world_db_session

    @staticmethod
    def creature_get_vendor_data_by_item(entry, item):
        world_db_session = SessionHolder()
        res = world_db_session.query(NpcVendor).filter_by(entry=entry, item=item).first()
        return res, world_db_session

    @staticmethod
    def creature_get_equipment_by_id(equipment_id):
        world_db_session = SessionHolder()
        res = world_db_session.query(CreatureEquipTemplate).filter_by(entry=equipment_id).first()
        world_db_session.close()
        return res

    class QuestRelationHolder:
        QUEST_RELATION = {}
        QUEST_INVOLVEMENT = {}

        @staticmethod
        def load_creature_quest(creature_quest_starter):
            if creature_quest_starter.entry not in WorldDatabaseManager.QuestRelationHolder.QUEST_RELATION:
                WorldDatabaseManager.QuestRelationHolder.QUEST_RELATION[creature_quest_starter.entry] = []

            WorldDatabaseManager.QuestRelationHolder.QUEST_RELATION[creature_quest_starter.entry]\
                .append(creature_quest_starter)

        @staticmethod
        def load_creature_involved_quest(creature_quest_involved_relation):
            if creature_quest_involved_relation.entry not in WorldDatabaseManager.QuestRelationHolder.QUEST_INVOLVEMENT:
                WorldDatabaseManager.QuestRelationHolder.QUEST_INVOLVEMENT[creature_quest_involved_relation.entry] = []

            WorldDatabaseManager.QuestRelationHolder.QUEST_INVOLVEMENT[creature_quest_involved_relation.entry]\
                .append(creature_quest_involved_relation)

        @staticmethod
        def creature_quest_get_by_entry(entry):
            return WorldDatabaseManager.QuestRelationHolder.QUEST_RELATION[entry] \
                if entry in WorldDatabaseManager.QuestRelationHolder.QUEST_RELATION else []

        @staticmethod
        def creature_involved_quest_get_by_entry(entry):
            return WorldDatabaseManager.QuestRelationHolder.QUEST_INVOLVEMENT[entry] \
                if entry in WorldDatabaseManager.QuestRelationHolder.QUEST_INVOLVEMENT else []

    @staticmethod
    def creature_quest_get_all():
        world_db_session = SessionHolder()
        res = world_db_session.query(t_creature_quest_starter).all()
        world_db_session.close()
        return res

    @staticmethod
    def creature_involved_quest_get_all():
        world_db_session = SessionHolder()
        res = world_db_session.query(t_creature_quest_finisher).all()
        world_db_session.close()
        return res

    # Quest stuff

    class QuestTemplateHolder:
        QUEST_TEMPLATES = {}

        @staticmethod
        def load_quest_template(quest_template):
            WorldDatabaseManager.QuestTemplateHolder.QUEST_TEMPLATES[quest_template.entry] = quest_template

        @staticmethod
        def quest_get_by_entry(entry):
            if entry in WorldDatabaseManager.QuestTemplateHolder.QUEST_TEMPLATES:
                return WorldDatabaseManager.QuestTemplateHolder.QUEST_TEMPLATES[entry]
            return None

    @staticmethod
    def quest_template_get_all():
        world_db_session = SessionHolder()
        res = world_db_session.query(QuestTemplate).filter_by(ignored=0).all()
        world_db_session.close()
        return res

    # Trainer stuff

    class TrainerSpellHolder:
        TRAINER_SPELLS: dict[tuple[int, int], NpcTrainer] = {}

        @staticmethod
        def load_trainer_spell(trainer_spell: NpcTrainer):
            WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS[(trainer_spell.template_entry, trainer_spell.spell)] = trainer_spell

    @staticmethod
    def trainer_spell_get_all() -> Optional[list[NpcTrainer]]:
        world_db_session: scoped_session = SessionHolder()
        res = world_db_session.query(NpcTrainer).all()
        world_db_session.close()
        return res

    @staticmethod
    def trainer_spells_get_by_trainer(trainer_entry_id: int) -> Optional[list[NpcTrainer]]:
        trainer_spells: list[NpcTrainer] = []
        
        creature_template: CreatureTemplate = WorldDatabaseManager.creature_get_by_entry(trainer_entry_id)
        trainer_template_id = creature_template.trainer_id

        for t_spell in WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS:
            if WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS[t_spell].template_entry == trainer_template_id:
                trainer_spells.append(WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS[t_spell])

        return trainer_spells if len(trainer_spells) > 0 else None

    @staticmethod
    def get_trainer_spell_by_trainer_id_and_spell(trainer_id: int, spell_id: int) -> Optional[NpcTrainer]:
        return WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS[(trainer_id, spell_id)] \
                if (trainer_id, spell_id) in WorldDatabaseManager.TrainerSpellHolder.TRAINER_SPELLS else None

    # Spell chain / trainer stuff (for chaining together spell ranks)

    class SpellChainHolder:
        SPELL_CHAINS: dict[int, SpellChain] = {}

        @staticmethod
        def load_spell_chain(spell_chain: SpellChain):
            WorldDatabaseManager.SpellChainHolder.SPELL_CHAINS[spell_chain.spell_id] = spell_chain
        
        @staticmethod
        def spell_chain_get_by_spell(spell_id: int):
            if spell_id in WorldDatabaseManager.SpellChainHolder.SPELL_CHAINS:
                return WorldDatabaseManager.SpellChainHolder.SPELL_CHAINS[spell_id]
            return None

    @staticmethod
    def spell_chain_get_all() -> Optional[list[SpellChain]]:
        world_db_session: scoped_session = SessionHolder()
        res = world_db_session.query(SpellChain).all()
        world_db_session.close()
        return res

