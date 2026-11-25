package dev.nc1107.packpack;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.MoveTowardsRestrictionGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Drowned;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;

/** Adjustments to sea creatures as they enter the world. All of them are safe to repeat on every load. */
public final class SeaLife {

    /** Big animals that read too small for a whole ocean world. */
    public static final TagKey<EntityType<?>> ENLARGED =
            TagKey.create(Registries.ENTITY_TYPE, ResourceLocation.fromNamespaceAndPath("packpack", "enlarged"));
    public static final double ENLARGED_SCALE = 1.5;

    /** Sharks also hunt drowned, which otherwise have the sea floor to themselves. */
    public static final TagKey<EntityType<?>> SHARKS =
            TagKey.create(Registries.ENTITY_TYPE, ResourceLocation.fromNamespaceAndPath("hapi", "all_sharks"));

    /**
     * Rare bosses that keep to the place they were first found, so meeting one is a choice:
     * they never follow a player across the map.
     */
    public static final TagKey<EntityType<?>> LAIR_BOSSES =
            TagKey.create(Registries.ENTITY_TYPE, ResourceLocation.fromNamespaceAndPath("packpack", "lair_bosses"));
    public static final int LAIR_RADIUS = 48;
    private static final String LAIR_KEY = "packpack_lair";

    private SeaLife() {
    }

    @SubscribeEvent
    public static void onJoin(EntityJoinLevelEvent event) {
        if (event.getLevel().isClientSide() || !(event.getEntity() instanceof Mob mob)) {
            return;
        }
        EntityType<?> type = mob.getType();
        if (type.is(ENLARGED)) {
            AttributeInstance scale = mob.getAttribute(Attributes.SCALE);
            if (scale != null) {
                scale.setBaseValue(ENLARGED_SCALE);
            }
        }
        if (type.is(SHARKS)) {
            mob.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(mob, Drowned.class, true));
        }
        if (type.is(LAIR_BOSSES) && mob instanceof PathfinderMob boss) {
            keepToLair(boss);
        }
    }

    private static void keepToLair(PathfinderMob boss) {
        CompoundTag data = boss.getPersistentData();
        BlockPos lair = NbtUtils.readBlockPos(data, LAIR_KEY).orElse(null);
        if (lair == null) {
            lair = boss.blockPosition();
            data.put(LAIR_KEY, NbtUtils.writeBlockPos(lair));
        }
        boss.restrictTo(lair, LAIR_RADIUS);
        boss.goalSelector.addGoal(1, new MoveTowardsRestrictionGoal(boss, 1.2));
        boss.setPersistenceRequired();
    }
}
