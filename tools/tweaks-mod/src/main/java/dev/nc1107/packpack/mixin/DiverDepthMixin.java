package dev.nc1107.packpack.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.ModifyConstant;

/**
 * Deep Seas lets a diver in the full Copper Diving Suit go down to 280 m, deeper than every
 * trench in this world (about 240 m), so the suit alone would reach anywhere. The pack's suit
 * holds 220 m instead: enough for the 200 m floor, not for the trenches, which later suits open up.
 */
@Pseudo
@Mixin(targets = "com.maxenonyme.createsubmarine.submarine.system.DiverPressure", remap = false)
public abstract class DiverDepthMixin {

    @Unique
    private static final int PACKPACK_SUIT_DEPTH = 220;

    @ModifyConstant(method = "onPlayerTick", constant = @Constant(intValue = 280), require = 1)
    private static int packpack$suitDepth(int deepSeasSuitDepth) {
        return PACKPACK_SUIT_DEPTH;
    }
}
