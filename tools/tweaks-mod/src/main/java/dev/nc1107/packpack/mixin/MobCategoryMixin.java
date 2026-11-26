package dev.nc1107.packpack.mixin;

import net.minecraft.world.entity.MobCategory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Small fish caps around each player. Hybrid Aquatic spawns its fish in a category of its own
 * (cap 10), not vanilla's WATER_AMBIENT, so with WATER_AMBIENT raised alone cod and salmon made
 * up about 100 of every 110 fish. About 100 small fish in all, most of them Hybrid Aquatic's.
 */
@Mixin(MobCategory.class)
public abstract class MobCategoryMixin {

    /** Cod, salmon, tropical fish and pufferfish; vanilla allows 20. */
    @Unique
    private static final int PACKPACK_WATER_AMBIENT_CAP = 40;

    @Unique
    private static final String PACKPACK_HYBRID_AQUATIC_FISH = "hybrid_aquatic:fish";

    @Unique
    private static final int PACKPACK_HYBRID_AQUATIC_FISH_CAP = 60;

    /** Squid, sharks, rays and the other bigger animals share this one; vanilla allows 5. */
    @Unique
    private static final int PACKPACK_WATER_CREATURE_CAP = 10;

    @Inject(method = "getMaxInstancesPerChunk", at = @At("HEAD"), cancellable = true)
    private void packpack$moreFish(CallbackInfoReturnable<Integer> cir) {
        MobCategory self = (MobCategory) (Object) this;
        if (self == MobCategory.WATER_AMBIENT) {
            cir.setReturnValue(PACKPACK_WATER_AMBIENT_CAP);
        } else if (self == MobCategory.WATER_CREATURE) {
            cir.setReturnValue(PACKPACK_WATER_CREATURE_CAP);
        } else if (self.getName().equals(PACKPACK_HYBRID_AQUATIC_FISH)) {
            cir.setReturnValue(PACKPACK_HYBRID_AQUATIC_FISH_CAP);
        }
    }
}
