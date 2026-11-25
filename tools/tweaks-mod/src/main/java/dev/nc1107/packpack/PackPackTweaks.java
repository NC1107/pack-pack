package dev.nc1107.packpack;

import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;

@Mod("packpack_tweaks")
public class PackPackTweaks {
    public PackPackTweaks() {
        NeoForge.EVENT_BUS.register(SeaLife.class);
    }
}
