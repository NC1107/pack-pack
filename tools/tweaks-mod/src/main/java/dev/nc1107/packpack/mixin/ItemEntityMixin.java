package dev.nc1107.packpack.mixin;

import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * In vanilla, items in water float up. With 175 blocks of sea, anything dropped (or lost on
 * death) ends up at the surface out of reach, so items sink slowly instead and come to rest on
 * the floor below where they were dropped. Applies to all water on both sides, so the client
 * predicts the same motion as the server.
 */
@Mixin(ItemEntity.class)
public abstract class ItemEntityMixin {

    @Unique
    private static final double PACKPACK_DRAG = 0.9;

    /** Downward pull per tick; with the drag that settles at about one block a second. */
    @Unique
    private static final double PACKPACK_SINK = 0.005;

    @Inject(method = "setUnderwaterMovement", at = @At("HEAD"), cancellable = true)
    private void packpack$sink(CallbackInfo ci) {
        ItemEntity self = (ItemEntity) (Object) this;
        Vec3 motion = self.getDeltaMovement();
        self.setDeltaMovement(motion.x * PACKPACK_DRAG, motion.y * PACKPACK_DRAG - PACKPACK_SINK, motion.z * PACKPACK_DRAG);
        ci.cancel();
    }
}
