package dev.nc1107.packpack;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;

@Mod(PackPackTweaks.MOD_ID)
public class PackPackTweaks {
    public static final String MOD_ID = "packpack_tweaks";

    public PackPackTweaks(IEventBus modBus) {
        RelicBlocks.register(modBus);
        NeoForge.EVENT_BUS.register(SeaLife.class);
        NeoForge.EVENT_BUS.register(LostSub.class);
        modBus.addListener(LostSub::requestLostCities);
    }
}
