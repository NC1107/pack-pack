package dev.nc1107.packpack.mixin;

import dev.nc1107.packpack.OuterSea;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.chunk.ChunkGenerator;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Hybrid Aquatic's spawn rules place each kind of animal relative to the sea level: most fish
 * from 32 under it to 8 over it, shallow ones in the 16 under it, deep ones 55 or more under it.
 * Under the Lost Worlds sea that put nearly everything in open water around y 63. Here they see
 * a sea level 32 blocks over the dome floor, so reef fish live over the floor and deep species
 * in the trenches. Air breathers (orcas, dolphins, manatees) are in HapiSurfaceSpawnRulesMixin.
 */
@Pseudo
@Mixin(targets = {
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseCephalopodEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseCritterEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseCrustaceanEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseFishEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseJellyfishEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseOctopusEntity$Companion",
        "dev.hybridlabs.hapi.entity.base.aquatic.BaseSharkEntity$Companion",
}, remap = false)
public abstract class HapiSpawnRulesMixin {

    @Redirect(method = "*", require = 0,
            at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/chunk/ChunkGenerator;getSeaLevel()I", remap = true))
    private int packpack$seaLevelOverTheFloor(ChunkGenerator generator) {
        return OuterSea.has(generator) ? OuterSea.SPAWN_SEA_LEVEL : generator.getSeaLevel();
    }

    /**
     * Most of these rules also want the sky visible straight up through the water. Under 175
     * blocks of sea that means nothing, and in a kelp forest (the start is in one) the kelp blocks
     * it from nearly every spot: no Hybrid Aquatic fish at all spawned around the start, even with
     * cod and salmon removed. Under the outer sea the check passes.
     */
    @Redirect(method = "*", require = 0,
            at = @At(value = "INVOKE", remap = false, target = "Ldev/hybridlabs/hapi/world/WorldHelper;"
                    + "canSeeSkyFromBelowWater(Lnet/minecraft/world/level/ServerLevelAccessor;Lnet/minecraft/core/BlockPos;)Z"))
    private boolean packpack$noSkyUnderTheSea(@Coerce Object helper, ServerLevelAccessor level, BlockPos pos) {
        if (OuterSea.level(level) != null) {
            return true;
        }
        try {
            return (boolean) helper.getClass().getMethod("canSeeSkyFromBelowWater", ServerLevelAccessor.class, BlockPos.class)
                    .invoke(helper, level, pos);
        } catch (ReflectiveOperationException e) {
            return true;
        }
    }
}
