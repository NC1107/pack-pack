package dev.nc1107.packpack;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;

/**
 * The air above the sea is toxic, which is why everyone lives under it and why sailing over the
 * top is no shortcut to the domes. With their head out of the water under open sky a player's
 * breath runs down as it does underwater and doesn't come back; once it's gone they take damage
 * every second. Anywhere with a roof overhead (a sub's cabin at the surface) is safe.
 */
public final class ToxicAir {

    private static final ResourceKey<DamageType> TOXIC_AIR = ResourceKey.create(
            Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath(PackPackTweaks.MOD_ID, "toxic_air"));
    /** Same as running out of air underwater: the counter goes to -20, then a hit, then it restarts. */
    private static final int OUT_OF_BREATH = -20;
    private static final float DAMAGE = 2.0f;

    /** Air at the start of each player's tick, before vanilla refills it for being out of water. */
    private static final Map<UUID, Integer> airBefore = new HashMap<>();
    private static final Map<UUID, Boolean> warned = new HashMap<>();

    private ToxicAir() {
    }

    @SubscribeEvent
    public static void beforeTick(PlayerTickEvent.Pre event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            airBefore.put(player.getUUID(), player.getAirSupply());
        }
    }

    @SubscribeEvent
    public static void afterTick(PlayerTickEvent.Post event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        Integer before = airBefore.remove(player.getUUID());
        if (before == null || !breathesToxicAir(player)) {
            warned.remove(player.getUUID());
            return;
        }
        int air = before - 1;
        if (air <= OUT_OF_BREATH) {
            air = 0;
            player.hurt(new DamageSource(player.level().registryAccess()
                    .registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(TOXIC_AIR)), DAMAGE);
        }
        player.setAirSupply(air);
        if (warned.putIfAbsent(player.getUUID(), true) == null) {
            player.displayClientMessage(Component.translatable("message.packpack_tweaks.toxic_air"), true);
        }
    }

    static boolean breathesToxicAir(ServerPlayer player) {
        if (player.isCreative() || player.isSpectator() || player.isEyeInFluid(FluidTags.WATER)) {
            return false;
        }
        Integer seaLevel = OuterSea.level(player.level());
        if (seaLevel == null || player.getEyeY() < seaLevel) {
            return false;
        }
        return player.level().canSeeSky(BlockPos.containing(player.getEyePosition()));
    }
}
