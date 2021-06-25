from struct import pack
from typing import Optional
from database.dbc.DbcModels import SkillLineAbility

from database.dbc.DbcDatabaseManager import DbcDatabaseManager
from network.packet.PacketWriter import PacketWriter, OpCode
from utils.constants.MiscCodes import TrainerServices, TrainerTypes

TALENT_SKILL_ID = 3
# Weapon, Attribute, Slayer, Magic, Defensive
SKILL_LINE_TALENT_IDS: list[int] = [222, 230, 231, 233, 234]


class TalentManager(object):
    def __init__(self, player_mgr):
        self.player_mgr = player_mgr

    def get_talent_cost_by_id(self, spell_id: int) -> int:
        spell_rank: int = DbcDatabaseManager.SpellHolder.spell_get_rank_by_id(spell_id)

        # We do know that Rank 1 cost 10 TP and Rank 2 cost 15 TP (https://i.imgur.com/eFi3cf4.jpg),
        # so we assume each rank cost 5 TP more.
        talent_points_cost: int = 10 + ((spell_rank - 1) * 5)
        return talent_points_cost

    def send_talent_list(self):
        next_talent: list[int] = []
        talent_bytes: bytes = b''
        talent_count: int = 0

        skill_line_abilities: list[SkillLineAbility] = DbcDatabaseManager.skill_line_ability_get_by_skill_lines(SKILL_LINE_TALENT_IDS)

        for ability in skill_line_abilities:
            # We only want the ones having an attached spell
            if not ability.Spell:
                continue

            spell: Optional[SkillLineAbility] = DbcDatabaseManager.SpellHolder.spell_get_by_id(ability.Spell)
            spell_rank: int = DbcDatabaseManager.SpellHolder.spell_get_rank_by_spell(spell)

            if ability.Spell in self.player_mgr.spell_manager.spells:
                if ability.SupercededBySpell > 0:
                    next_talent.append(ability.SupercededBySpell)
                status = TrainerServices.TRAINER_SERVICE_USED
            else:
                if ability.Spell in next_talent:
                    status = TrainerServices.TRAINER_SERVICE_AVAILABLE
                elif spell_rank == 1:
                    status = TrainerServices.TRAINER_SERVICE_AVAILABLE
                else:
                    status = TrainerServices.TRAINER_SERVICE_UNAVAILABLE

            
            talent_points_cost = self.get_talent_cost_by_id(ability.Spell)
            data = pack('<IBI3B6I',
                        ability.Spell,  # Spell id
                        status,  # Status
                        0,  # Cost
                        talent_points_cost,  # Talent Point Cost
                        0,  # Skill Point Cost
                        spell.BaseLevel,  # Required Level
                        0,  # Required Skill Line
                        0,  # Required Skill Rank
                        0,  # Required Skill Step
                        ability.custom_PrecededBySpell,  # Required Ability (1)
                        0,  # Required Ability (2)
                        0  # Required Ability (3)
                        )
            talent_bytes += data
            talent_count += 1

        data = pack('<Q2I', self.player_mgr.guid, TrainerTypes.TRAINER_TYPE_TALENTS, talent_count) + talent_bytes
        self.player_mgr.session.enqueue_packet(PacketWriter.get_packet(OpCode.SMSG_TRAINER_LIST, data))
