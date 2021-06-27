from __future__ import annotations
 #REMOVE THIS & TYPE HINTING BEFORE PR
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game.world.managers.objects.spell.SpellManager import SpellManager
    from game.world.managers.objects.spell.CastingSpell import CastingSpell
    from game.world.managers.objects.spell.SpellEffect import SpellEffect
    from game.world.managers.objects.player.PlayerManager import PlayerManager

from database.world.WorldDatabaseManager import WorldDatabaseManager
from game.world.managers.objects.player.DuelManager import DuelManager
from game.world.managers.objects.spell.AuraManager import AppliedAura
from utils.Logger import Logger
from utils.constants.MiscCodes import ObjectTypes, HighGuid
from utils.constants.SpellCodes import SpellCastFlags, SpellCheckCastResult, AuraTypes, SpellEffects, SpellState
from utils.constants.UnitCodes import PowerTypes, UnitFlags, MovementTypes


class SpellEffectHandler(object):
    @staticmethod
    def apply_effect(casting_spell, effect, caster, target):
        if effect.effect_type not in SPELL_EFFECTS:
            Logger.debug(f'Unimplemented effect called: {effect.effect_type}')
            return
        SPELL_EFFECTS[effect.effect_type](casting_spell, effect, caster, target)

    @staticmethod
    def handle_school_damage(casting_spell, effect, caster, target):
        damage = effect.get_effect_points(casting_spell.caster_effective_level)
        caster.deal_spell_damage(target, damage, casting_spell.spell_entry.School, casting_spell.spell_entry.ID)

    @staticmethod
    def handle_heal(casting_spell, effect, caster, target):
        healing = effect.get_effect_points(casting_spell.caster_effective_level)
        caster.deal_spell_healing(target, healing, casting_spell.spell_entry.School, casting_spell.spell_entry.ID)

    @staticmethod
    def handle_weapon_damage(casting_spell, effect, caster, target):
        damage_info = caster.calculate_melee_damage(target, casting_spell.spell_attack_type)
        if not damage_info:
            return
        damage = damage_info.total_damage + effect.get_effect_points(casting_spell.caster_effective_level)
        caster.deal_spell_damage(target, damage, casting_spell.spell_entry.School, casting_spell.spell_entry.ID)

    @staticmethod
    def handle_weapon_damage_plus(casting_spell, effect, caster, target):
        damage_info = caster.calculate_melee_damage(target, casting_spell.spell_attack_type)
        if not damage_info:
            return
        damage = damage_info.total_damage
        damage_bonus = effect.get_effect_points(casting_spell.caster_effective_level)

        if caster.get_type() == ObjectTypes.TYPE_PLAYER and \
                casting_spell.requires_combo_points():
            damage_bonus *= caster.combo_points

        caster.deal_spell_damage(target, damage + damage_bonus, casting_spell.spell_entry.School, casting_spell.spell_entry.ID)

    @staticmethod
    def handle_add_combo_points(casting_spell, effect, caster, target):
        caster.add_combo_points_on_target(target, effect.get_effect_points(casting_spell.caster_effective_level))

    @staticmethod
    def handle_aura_application(casting_spell, effect, caster, target):
        target.aura_manager.apply_spell_effect_aura(caster, casting_spell, effect)

    @staticmethod
    def handle_request_duel(casting_spell, effect, caster, target):
        duel_result = DuelManager.request_duel(caster, target, effect.misc_value)
        if duel_result == 1:
            result = SpellCheckCastResult.SPELL_NO_ERROR
        elif duel_result == 0:
            result = SpellCheckCastResult.SPELL_FAILED_TARGET_DUELING
        else:
            result = SpellCheckCastResult.SPELL_FAILED_DONT_REPORT
        caster.spell_manager.send_cast_result(casting_spell.spell_entry.ID, result)

    @staticmethod
    def handle_open_lock(casting_spell, effect, caster, target):
        if caster and target:
            target.use(caster)

    @staticmethod
    def handle_energize(casting_spell, effect, caster, target):
        power_type = effect.misc_value

        if power_type != target.power_type:
            return

        new_power = target.get_power_type_value() + effect.get_effect_points(casting_spell.caster_effective_level)
        if power_type == PowerTypes.TYPE_MANA:
            target.set_mana(new_power)
        elif power_type == PowerTypes.TYPE_RAGE:
            target.set_rage(new_power)
        elif power_type == PowerTypes.TYPE_FOCUS:
            target.set_focus(new_power)
        elif power_type == PowerTypes.TYPE_ENERGY:
            target.set_energy(new_power)

    @staticmethod
    def handle_summon_mount(casting_spell, effect, caster, target):
        already_mounted = target.unit_flags & UnitFlags.UNIT_MASK_MOUNTED
        if already_mounted:
            # Remove any existing mount auras.
            target.aura_manager.remove_auras_by_type(AuraTypes.SPELL_AURA_MOUNTED)
            target.aura_manager.remove_auras_by_type(AuraTypes.SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED)
            # Force dismount if target is still mounted (like a previous SPELL_EFFECT_SUMMON_MOUNT that doesn't
            # leave any applied aura).
            if target.mount_display_id > 0:
                target.unmount()
                target.set_dirty()
        else:
            creature_entry = effect.misc_value
            if not target.summon_mount(creature_entry):
                Logger.error(f'SPELL_EFFECT_SUMMON_MOUNT: Creature template ({creature_entry}) not found in database.')

    @staticmethod
    def handle_insta_kill(casting_spell, effect, caster, target):
        # No SMSG_SPELLINSTAKILLLOG in 0.5.3
        target.die(killer=caster)

    @staticmethod
    def handle_create_item(casting_spell, effect, caster, target):
        if target.get_type() != ObjectTypes.TYPE_PLAYER:
            return

        target.inventory.add_item(effect.item_type,
                                  count=effect.get_effect_points(casting_spell.caster_effective_level))

    @staticmethod
    def handle_teleport_units(casting_spell, effect, caster, target):
        resolved_targets = effect.targets.resolved_targets_b
        if not resolved_targets or len(resolved_targets) == 0:
            return
        teleport_info = resolved_targets[0]

        target.teleport(teleport_info[0], teleport_info[1])  # map, coordinates resolved
        # TODO Die sides are assigned for at least Word of Recall (ID 1)

    @staticmethod
    def handle_persistent_area_aura(casting_spell, effect, caster, target):  # Ground-targeted aoe
        if target is not None:
            return

        SpellEffectHandler.handle_apply_area_aura(casting_spell, effect, caster, target)
        return

    @staticmethod
    def handle_leap(casting_spell: CastingSpell, effect: SpellEffect, caster: PlayerManager, target): # Blink, Charge (alpha)
        target_teleport_info = effect.targets.initial_target
        if not target_teleport_info:
            return

        from game.world.managers.abstractions.Vector import Vector
        teleport_dest_final = Vector(target_teleport_info.x, target_teleport_info.y, target_teleport_info.z, caster.location.o)
        
        if caster.location.distance(teleport_dest_final) <= casting_spell.range_entry.RangeMax:
            caster.teleport(caster.map_, teleport_dest_final)
        else: # If target out of bounds, teleport player in the same direction at max dist possible
            from_loc = caster.location
            to_loc = teleport_dest_final

            d1 = from_loc.distance(to_loc)
            d2 = casting_spell.range_entry.RangeMax

            tele_point_x = from_loc.x - ((d2 * (from_loc.x - to_loc.x)) / d1)
            tele_point_y = from_loc.y - ((d2 * (from_loc.y - to_loc.y)) / d1)
            tele_point_z = Vector.calculate_z(tele_point_x, tele_point_y, caster.map_, to_loc.z) # Maps required TODO vmaps required to work properly on large world obejcts (ex. Stormwind, caves etc.), with maps it only finds ground position.

            adjusted_teleport_dest = Vector(tele_point_x, tele_point_y, tele_point_z, from_loc.o)

            caster.teleport(caster.map_, adjusted_teleport_dest)

    @staticmethod
    def handle_apply_area_aura(casting_spell, effect, caster, target):  # Paladin auras, healing stream totem etc.
        casting_spell.cast_state = SpellState.SPELL_STATE_ACTIVE

        previous_targets = effect.targets.previous_targets_a if effect.targets.previous_targets_a else []
        current_targets = effect.targets.resolved_targets_a

        new_targets = [unit for unit in current_targets if unit not in previous_targets]  # Targets that can't have the aura yet
        missing_targets = [unit for unit in previous_targets if unit not in current_targets]  # Targets that moved out of the area

        for target in new_targets:
            new_aura = AppliedAura(caster, casting_spell, effect, target)
            new_aura.aura_period_timestamps = effect.effect_aura.aura_period_timestamps.copy()  # Don't pass reference, AuraManager will manage timestamps
            new_aura.duration = effect.effect_aura.duration
            target.aura_manager.add_aura(new_aura)

        if effect.effect_aura.is_past_next_period_timestamp():
            effect.effect_aura.pop_period_timestamp()  # Update effect aura timestamps

        for target in missing_targets:
            target.aura_manager.cancel_auras_by_spell_id(casting_spell.spell_entry.ID)

    @staticmethod
    def handle_learn_spell(casting_spell, effect, caster, target):
        target_spell_id = effect.trigger_spell_id
        target.spell_manager.learn_spell(target_spell_id)

    @staticmethod
    def handle_summon_totem(casting_spell, effect, caster, target):
        totem_entry = effect.misc_value

        # TODO Temporary way to spawn creature
        creature_template = WorldDatabaseManager.creature_get_by_entry(totem_entry)
        from database.world.WorldModels import SpawnsCreatures
        instance = SpawnsCreatures()
        instance.spawn_id = HighGuid.HIGHGUID_UNIT + 1000  # TODO Placeholder GUID
        instance.map = caster.map_
        instance.orientation = target.o
        instance.position_x = target.x
        instance.position_y = target.y
        instance.position_z = target.z
        instance.spawntimesecsmin = 0
        instance.spawntimesecsmax = 0
        instance.health_percent = 100
        instance.mana_percent = 100
        instance.movement_type = MovementTypes.IDLE
        instance.spawn_flags = 0
        instance.visibility_mod = 0

        from game.world.managers.objects.creature.CreatureManager import CreatureManager
        creature_manager = CreatureManager(
            creature_template=creature_template,
            creature_instance=instance
        )
        creature_manager.faction = caster.faction

        creature_manager.load()
        creature_manager.set_dirty()
        creature_manager.respawn()

        # TODO This should be handled in creature AI instead
        # TODO Totems are not connected to player (pet etc. handling)
        for spell_id in [creature_template.spell_id1, creature_template.spell_id2, creature_template.spell_id3, creature_template.spell_id4]:
            if spell_id == 0:
                break
            creature_manager.spell_manager.handle_cast_attempt(spell_id, creature_manager, creature_manager, 0)


    AREA_SPELL_EFFECTS = [
        SpellEffects.SPELL_EFFECT_PERSISTENT_AREA_AURA,
        SpellEffects.SPELL_EFFECT_APPLY_AREA_AURA
    ]


SPELL_EFFECTS = {
    SpellEffects.SPELL_EFFECT_SCHOOL_DAMAGE: SpellEffectHandler.handle_school_damage,
    SpellEffects.SPELL_EFFECT_HEAL: SpellEffectHandler.handle_heal,
    SpellEffects.SPELL_EFFECT_WEAPON_DAMAGE: SpellEffectHandler.handle_weapon_damage,
    SpellEffects.SPELL_EFFECT_ADD_COMBO_POINTS: SpellEffectHandler.handle_add_combo_points,
    SpellEffects.SPELL_EFFECT_DUEL: SpellEffectHandler.handle_request_duel,
    SpellEffects.SPELL_EFFECT_WEAPON_DAMAGE_PLUS: SpellEffectHandler.handle_weapon_damage_plus,
    SpellEffects.SPELL_EFFECT_APPLY_AURA: SpellEffectHandler.handle_aura_application,
    SpellEffects.SPELL_EFFECT_ENERGIZE: SpellEffectHandler.handle_energize,
    SpellEffects.SPELL_EFFECT_SUMMON_MOUNT: SpellEffectHandler.handle_summon_mount,
    SpellEffects.SPELL_EFFECT_INSTAKILL: SpellEffectHandler.handle_insta_kill,
    SpellEffects.SPELL_EFFECT_CREATE_ITEM: SpellEffectHandler.handle_create_item,
    SpellEffects.SPELL_EFFECT_TELEPORT_UNITS: SpellEffectHandler.handle_teleport_units,
    SpellEffects.SPELL_EFFECT_PERSISTENT_AREA_AURA: SpellEffectHandler.handle_persistent_area_aura,
    SpellEffects.SPELL_EFFECT_OPEN_LOCK: SpellEffectHandler.handle_open_lock,
    SpellEffects.SPELL_EFFECT_LEARN_SPELL: SpellEffectHandler.handle_learn_spell,
    SpellEffects.SPELL_EFFECT_LEAP: SpellEffectHandler.handle_leap,
    SpellEffects.SPELL_EFFECT_APPLY_AREA_AURA: SpellEffectHandler.handle_apply_area_aura,
    SpellEffects.SPELL_EFFECT_SUMMON_TOTEM: SpellEffectHandler.handle_summon_totem
}

