package dev.nc1107.packpack.mixin;

import net.minecraft.world.level.levelgen.feature.KelpFeature;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.ModifyConstant;

@Mixin(KelpFeature.class)
public class KelpFeatureMixin {
    /** Generated kelp is 1 to 75 blocks tall instead of 1 to 10. */
    @ModifyConstant(method = "place", constant = @Constant(intValue = 10))
    private int packpack$tallKelp(int vanilla) {
        return 75;
    }
}
