package dev.nc1107.packpack.mixin;

import net.minecraft.world.entity.MobCategory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Vanilla allows 20 small fish around each player, this allows 100. In a world that is almost all ocean, with
 * dozens of species from Hybrid Aquatic sharing that cap, schools stay sparse and most species
 * are rarely seen, so the cap is higher.
 */
@Mixin(MobCategory.class)
public abstract class MobCategoryMixin {

    @Unique
    private static final int PACKPACK_WATER_AMBIENT_CAP = 100;

    /** Squid, sharks, rays and the other bigger animals share this one; vanilla allows 5. */
    @Unique
    private static final int PACKPACK_WATER_CREATURE_CAP = 10;

    @Inject(method = "getMaxInstancesPerChunk", at = @At("HEAD"), cancellable = true)
    private void packpack$moreFish(CallbackInfoReturnable<Integer> cir) {
        if ((Object) this == MobCategory.WATER_AMBIENT) {
            cir.setReturnValue(PACKPACK_WATER_AMBIENT_CAP);
        } else if ((Object) this == MobCategory.WATER_CREATURE) {
            cir.setReturnValue(PACKPACK_WATER_CREATURE_CAP);
        }
    }
}
