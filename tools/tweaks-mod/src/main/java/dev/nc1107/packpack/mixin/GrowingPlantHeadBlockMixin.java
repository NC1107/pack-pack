package dev.nc1107.packpack.mixin;

import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.GrowingPlantHeadBlock;
import net.minecraft.world.level.block.KelpBlock;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(GrowingPlantHeadBlock.class)
public class GrowingPlantHeadBlockMixin {
    /**
     * Kelp stops growing when its head reaches age 25. A new head never gets older than 24,
     * so kelp keeps growing until it runs out of water.
     */
    @Inject(method = "getGrowIntoState", at = @At("HEAD"), cancellable = true)
    private void packpack$endlessKelp(BlockState state, RandomSource random, CallbackInfoReturnable<BlockState> cir) {
        if ((Object) this instanceof KelpBlock) {
            int age = state.getValue(GrowingPlantHeadBlock.AGE);
            cir.setReturnValue(state.setValue(GrowingPlantHeadBlock.AGE, Math.min(age + 1, 24)));
        }
    }
}
