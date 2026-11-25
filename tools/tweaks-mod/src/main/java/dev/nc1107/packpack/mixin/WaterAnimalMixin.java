package dev.nc1107.packpack.mixin;

import java.lang.reflect.Method;
import java.util.Arrays;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.animal.WaterAnimal;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.ChunkGenerator;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Vanilla spawns small fish in the 13 blocks under the world's sea level, which under the Lost
 * Worlds sea is a thin band in the middle of the water (y 50 to 63), nowhere near the reefs.
 * Under that sea, small fish spawn anywhere in the water instead, as long as the floor or a
 * reef is close below them, because that is where they live. Kelp does not count, since it
 * grows most of the way to the surface.
 */
@Mixin(WaterAnimal.class)
public abstract class WaterAnimalMixin {

    @Unique
    private static final int PACKPACK_MAX_HEIGHT_OVER_FLOOR = 6;

    /** Lost Worlds' generator, found by name so this mod does not have to depend on it. */
    @Unique
    private static final ClassValue<Method> PACKPACK_OUTER_SEA_LEVEL = new ClassValue<>() {
        @Override
        protected Method computeValue(Class<?> type) {
            for (Class<?> c = type; c != null; c = c.getSuperclass()) {
                boolean lostWorlds = Arrays.stream(c.getInterfaces())
                        .anyMatch(i -> i.getName().equals("mcjty.lostcities.api.ILostWorldsChunkGenerator"));
                if (lostWorlds) {
                    try {
                        return c.getMethod("getOuterSeaLevel");
                    } catch (NoSuchMethodException e) {
                        return null;
                    }
                }
            }
            return null;
        }
    };

    @Inject(method = "checkSurfaceWaterAnimalSpawnRules", at = @At("HEAD"), cancellable = true)
    private static void packpack$spawnOverTheFloor(EntityType<? extends WaterAnimal> type, LevelAccessor level,
                                                   MobSpawnType reason, BlockPos pos, RandomSource random,
                                                   CallbackInfoReturnable<Boolean> cir) {
        if (type.getCategory() != MobCategory.WATER_AMBIENT || !packpack$underOuterSea(level)) {
            return;
        }
        boolean inWater = level.getFluidState(pos.below()).is(FluidTags.WATER)
                && level.getBlockState(pos.above()).is(Blocks.WATER);
        cir.setReturnValue(inWater && packpack$nearFloor(level, pos));
    }

    @Unique
    private static boolean packpack$underOuterSea(LevelAccessor level) {
        if (!(level instanceof ServerLevelAccessor server)) {
            return false;
        }
        ChunkGenerator generator = server.getLevel().getChunkSource().getGenerator();
        Method outerSeaLevel = PACKPACK_OUTER_SEA_LEVEL.get(generator.getClass());
        try {
            return outerSeaLevel != null && outerSeaLevel.invoke(generator) != null;
        } catch (ReflectiveOperationException e) {
            return false;
        }
    }

    @Unique
    private static boolean packpack$nearFloor(LevelAccessor level, BlockPos pos) {
        for (int depth = 2; depth <= PACKPACK_MAX_HEIGHT_OVER_FLOOR; depth++) {
            if (level.getBlockState(pos.below(depth)).isSolid()) {
                return true;
            }
        }
        return false;
    }
}
