package dev.nc1107.packpack.mixin;

import dev.nc1107.packpack.OuterSea;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.animal.WaterAnimal;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Blocks;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Vanilla spawns sea life in the 13 blocks under the world's sea level, which under the Lost
 * Worlds sea is a thin band in the middle of the water (y 50 to 63). Under that sea instead:
 * small fish spawn anywhere as long as the floor or a reef is close below them, because that is
 * where they live (kelp does not count, it grows most of the way to the surface); dolphins
 * spawn in the 13 blocks under the real surface, where they can breathe; squid and other water
 * creatures spawn anywhere in the water.
 */
@Mixin(WaterAnimal.class)
public abstract class WaterAnimalMixin {

    @Unique
    private static final int PACKPACK_MAX_HEIGHT_OVER_FLOOR = 6;

    @Inject(method = "checkSurfaceWaterAnimalSpawnRules", at = @At("HEAD"), cancellable = true)
    private static void packpack$spawnOverTheFloor(EntityType<? extends WaterAnimal> type, LevelAccessor level,
                                                   MobSpawnType reason, BlockPos pos, RandomSource random,
                                                   CallbackInfoReturnable<Boolean> cir) {
        Integer surface = OuterSea.level(level);
        MobCategory category = type.getCategory();
        if (surface == null || (category != MobCategory.WATER_AMBIENT && category != MobCategory.WATER_CREATURE)) {
            return;
        }
        boolean inWater = level.getFluidState(pos.below()).is(FluidTags.WATER)
                && level.getBlockState(pos.above()).is(Blocks.WATER);
        if (category == MobCategory.WATER_AMBIENT) {
            cir.setReturnValue(inWater && packpack$nearFloor(level, pos));
        } else if (type == EntityType.DOLPHIN) {
            cir.setReturnValue(inWater && pos.getY() >= surface - 13 && pos.getY() <= surface);
        } else {
            cir.setReturnValue(inWater);
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
