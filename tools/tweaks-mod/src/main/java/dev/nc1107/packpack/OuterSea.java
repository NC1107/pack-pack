package dev.nc1107.packpack;

import java.lang.reflect.Method;
import java.util.Arrays;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.chunk.ChunkGenerator;

/**
 * Whether a world is under a Lost Worlds outer sea. Lost Worlds' generator is found by the name of
 * the Lost Cities interface it implements, so this mod does not depend on either.
 */
public final class OuterSea {

    /**
     * The sea level spawn rules should see under the outer sea: 32 blocks over the dome floor
     * (y -13). Mobs that spawn "near the surface" then spawn over the sea floor, where the reefs
     * and kelp are, instead of in a band at y 63 in the middle of 175 blocks of water.
     */
    public static final int SPAWN_SEA_LEVEL = 19;

    private static final ClassValue<Method> OUTER_SEA_LEVEL = new ClassValue<>() {
        @Override
        protected Method computeValue(Class<?> type) {
            for (Class<?> c = type; c != null; c = c.getSuperclass()) {
                boolean lostWorlds = Arrays.stream(c.getInterfaces())
                        .anyMatch(i -> i.getName().equals("mcjty.lostcities.api.ILostWorldsChunkGenerator"));
                if (lostWorlds) {
                    try {
                        return c.getMethod("getOuterSeaLevel");
                    } catch (NoSuchMethodException e) {
                        return null;
                    }
                }
            }
            return null;
        }
    };

    private OuterSea() {
    }

    public static boolean has(ChunkGenerator generator) {
        Method outerSeaLevel = OUTER_SEA_LEVEL.get(generator.getClass());
        try {
            return outerSeaLevel != null && outerSeaLevel.invoke(generator) != null;
        } catch (ReflectiveOperationException e) {
            return false;
        }
    }

    public static boolean has(LevelAccessor level) {
        return level instanceof ServerLevelAccessor server && has(server.getLevel().getChunkSource().getGenerator());
    }
}
