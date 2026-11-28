package dev.nc1107.packpack;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.Function;
import mcjty.lostcities.api.ILostCities;
import mcjty.lostcities.api.ILostCityInformation;
import mcjty.lostcities.api.ILostSphere;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.InterModComms;
import net.neoforged.fml.event.lifecycle.InterModEnqueueEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import org.slf4j.Logger;
import com.mojang.logging.LogUtils;

/**
 * Players respawn at the world spawn, which is inside the start sub on the sea floor. If the sub
 * has been flooded or taken apart that spot is under 200 metres of water and the player would die
 * again at once, forever. Then they wake up in a dome instead, somewhere random in one of the
 * nearest few, with a diving suit and a full backtank, and that dome becomes their spawn.
 */
public final class LostSub {

    /**
     * Lost Cities can put a sphere in the middle of every 16 by 16 chunk cell (128 + 256k blocks),
     * and only answers for points inside a sphere, so those centres are what to ask about.
     */
    private static final int SEARCH_STEP = 256;
    private static final int SEARCH_OFFSET = 128;
    private static final int SEARCH_RINGS = 24;
    private static final int DOMES_TO_PICK_FROM = 4;

    private static final String[] KIT = {
            "create:copper_diving_helmet", "create_submarine:diving_chestplate",
            "create_submarine:diving_leggings", "create:copper_diving_boots", "create:copper_backtank",
    };
    private static final ResourceLocation BACKTANK_AIR = ResourceLocation.parse("create:banktank_air");
    private static final int FULL_BACKTANK = 900;

    private static final Logger LOGGER = LogUtils.getLogger();

    private static volatile ILostCities lostCities;

    private LostSub() {
    }

    static void requestLostCities(InterModEnqueueEvent event) {
        InterModComms.sendTo(ILostCities.LOSTCITIES, ILostCities.GET_LOST_CITIES,
                () -> (Function<ILostCities, Void>) api -> {
                    lostCities = api;
                    return null;
                });
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent event) {
        if (event.isEndConquered() || !(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        ServerLevel level = player.serverLevel();
        if (OuterSea.level(level) == null
                || !level.getFluidState(BlockPos.containing(player.getEyePosition())).is(FluidTags.WATER)) {
            return;
        }
        BlockPos spot = domeSpot(level, player.getRandom());
        if (spot == null) {
            LOGGER.warn("{} respawned in the sea and no dome was found to move them to (Lost Cities API {})",
                    player.getName().getString(), lostCities == null ? "missing" : "present");
            return;
        }
        boolean ownSpawn = hasOwnSpawn(player);
        LOGGER.info("{} respawned in the sea ({}): moved to a dome at {}", player.getName().getString(),
                ownSpawn ? "their bed is under water" : "the start sub is gone", spot);
        player.teleportTo(level, spot.getX() + 0.5, spot.getY(), spot.getZ() + 0.5, Set.of(), player.getYRot(), 0);
        player.setRespawnPosition(level.dimension(), spot, 0, true, false);
        if (!ownSpawn) {
            for (String id : KIT) {
                player.getInventory().placeItemBackInInventory(kitItem(id));
            }
        }
        player.sendSystemMessage(Component.literal(ownSpawn
                ? "Your bed is under water. Someone pulled you out and brought you to a dome."
                : "Your sub is gone. Someone pulled you out of the water and brought you to a dome."));
    }

    /**
     * Anyone who respawns under the sea is moved, or they would die there forever. The suit is
     * only for those the pack put there: the world spawn (no respawn position) and the dome
     * spot set here (forced). A bed is the player's own doing, and one left under water would
     * otherwise hand out a fresh suit on every death.
     */
    private static boolean hasOwnSpawn(ServerPlayer player) {
        return player.getRespawnPosition() != null && !player.isRespawnForced();
    }

    private static ItemStack kitItem(String id) {
        ItemStack stack = new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
        @SuppressWarnings("unchecked")
        DataComponentType<Integer> air = (DataComponentType<Integer>) BuiltInRegistries.DATA_COMPONENT_TYPE.get(BACKTANK_AIR);
        if (id.endsWith("backtank") && air != null) {
            stack.set(air, FULL_BACKTANK);
        }
        return stack;
    }

    /** A random place to stand inside one of the domes nearest the world origin. */
    private static BlockPos domeSpot(ServerLevel level, RandomSource random) {
        ILostCityInformation info = lostCities == null ? null : lostCities.getLostInfo(level);
        if (info == null) {
            return null;
        }
        List<ILostSphere> domes = nearestDomes(info);
        while (!domes.isEmpty()) {
            ILostSphere dome = domes.remove(random.nextInt(domes.size()));
            BlockPos spot = standingSpot(level, dome, random);
            if (spot != null) {
                return spot;
            }
        }
        return null;
    }

    private static List<ILostSphere> nearestDomes(ILostCityInformation info) {
        List<ILostSphere> domes = new ArrayList<>();
        Set<BlockPos> seen = new HashSet<>();
        for (int ring = 1; ring <= SEARCH_RINGS && domes.size() < DOMES_TO_PICK_FROM; ring++) {
            for (int i = -ring; i <= ring; i++) {
                for (int[] cell : new int[][]{{i, -ring}, {i, ring}, {-ring, i}, {ring, i}}) {
                    ILostSphere sphere = info.getSphere(cell[0] * SEARCH_STEP + SEARCH_OFFSET, cell[1] * SEARCH_STEP + SEARCH_OFFSET);
                    if (sphere != null && sphere.isEnabled() && sphere.getCenterPos() != null && seen.add(sphere.getCenterPos())) {
                        domes.add(sphere);
                    }
                }
            }
        }
        return domes;
    }

    /** Somewhere in the middle half of the dome with solid ground under two blocks of air. */
    private static BlockPos standingSpot(ServerLevel level, ILostSphere dome, RandomSource random) {
        BlockPos centre = dome.getCenterPos();
        float reach = dome.getRadius() * 0.5f;
        for (int attempt = 0; attempt < 32; attempt++) {
            double angle = random.nextDouble() * Math.PI * 2;
            double distance = reach * Math.sqrt(random.nextDouble());
            int x = centre.getX() + (int) Math.round(Math.cos(angle) * distance);
            int z = centre.getZ() + (int) Math.round(Math.sin(angle) * distance);
            for (int y = centre.getY() + (int) reach; y > centre.getY() - 8; y--) {
                BlockPos feet = new BlockPos(x, y, z);
                BlockPos ground = feet.below();
                if (level.getBlockState(feet).isAir() && level.getBlockState(feet.above()).isAir()
                        && level.getBlockState(ground).isFaceSturdy(level, ground, Direction.UP)) {
                    return feet;
                }
            }
        }
        return null;
    }
}
