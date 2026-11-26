package dev.nc1107.packpack;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;

@Mod("packpack_tweaks")
public class PackPackTweaks {
    public PackPackTweaks(IEventBus modBus) {
        NeoForge.EVENT_BUS.register(SeaLife.class);
        NeoForge.EVENT_BUS.register(LostSub.class);
        modBus.addListener(LostSub::requestLostCities);
    }
}
