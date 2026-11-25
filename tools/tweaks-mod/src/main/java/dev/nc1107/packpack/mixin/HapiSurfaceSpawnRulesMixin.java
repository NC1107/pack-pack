package dev.nc1107.packpack.mixin;

import dev.nc1107.packpack.OuterSea;
import net.minecraft.world.level.chunk.ChunkGenerator;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Hybrid Aquatic's air breathers (orcas and its dolphins, manatees and dugongs) spawn relative to
 * the sea level, which under the Lost Worlds sea is y 63, more than 90 blocks under the real
 * surface. They see the real surface instead, so they spawn where they can breathe.
 */
@Pseudo
@Mixin(targets = {
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseDolphinEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseSirenianEntity$Companion",
}, remap = false)
public abstract class HapiSurfaceSpawnRulesMixin {

    @Redirect(method = "*", require = 0,
            at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/chunk/ChunkGenerator;getSeaLevel()I", remap = true))
    private int packpack$realSurface(ChunkGenerator generator) {
        Integer surface = OuterSea.level(generator);
        return surface != null ? surface : generator.getSeaLevel();
    }
}
