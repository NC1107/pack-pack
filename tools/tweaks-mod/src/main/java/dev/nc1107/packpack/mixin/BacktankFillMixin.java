package dev.nc1107.packpack.mixin;

import net.minecraft.util.Mth;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * A placed Create backtank fills from rotation, one unit of air after a wait that is 13 ticks at
 * a hand crank's 32 RPM: ten and a half minutes of cranking for the fifteen minutes of air in a
 * full tank. The hand pump in the start sub is the only air there is at first, so the wait is
 * capped and a full tank takes a little over two minutes by hand. Fast shafts already had no wait.
 */
@Pseudo
@Mixin(targets = "com.simibubi.create.content.equipment.armor.BacktankBlockEntity", remap = false)
public abstract class BacktankFillMixin {

    @Unique
    private static final int PACKPACK_LONGEST_WAIT_TICKS = 2;

    @Redirect(method = "tick", require = 1,
            at = @At(value = "INVOKE", target = "Lnet/minecraft/util/Mth;clamp(III)I", ordinal = 1, remap = true))
    private int packpack$shorterWait(int wait, int shortest, int longest) {
        return Mth.clamp(wait, shortest, Math.min(longest, PACKPACK_LONGEST_WAIT_TICKS));
    }
}
