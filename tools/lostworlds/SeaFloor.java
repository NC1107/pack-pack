package mcjty.lostworlds.worldgen;

import net.minecraft.util.Mth;
import net.minecraft.world.level.levelgen.synth.ImprovedNoise;
import net.minecraft.world.level.levelgen.XoroshiroRandomSource;

/**
 * Height of the sea floor outside Lost Cities domes: broad plates, mid ocean ridges, trenches,
 * seamounts and a little fine relief. A pure function of block x and z, so chunks never
 * disagree at their borders and structure placement can ask for it before a chunk exists.
 *
 * The floor is flat around every possible dome position (Lost Cities puts a dome on a 256
 * block grid, 128 offset, when grid32 is off) and around the world origin, where players start.
 */
public final class SeaFloor {
    public static final int BASE = -13;
    public static final int MIN = -56;
    public static final int MAX = 72;
    public static final int SAND_DEPTH = 30;

    private static final double GRID = 256.0;
    private static final double GRID_OFFSET = 128.0;
    private static final double DOME_FLAT = 92.0;
    private static final double DOME_BLEND = 126.0;
    private static final double SPAWN_FLAT = 45.0;
    private static final double SPAWN_BLEND = 90.0;

    private static final ImprovedNoise PLATE = noise(11);
    private static final ImprovedNoise RIDGE = noise(12);
    private static final ImprovedNoise RIDGE_MASK = noise(13);
    private static final ImprovedNoise TRENCH = noise(14);
    private static final ImprovedNoise MOUNT = noise(15);
    private static final ImprovedNoise DETAIL = noise(16);
    private static final ImprovedNoise HILL = noise(19);
    private static final ImprovedNoise WARP_X = noise(17);
    private static final ImprovedNoise WARP_Z = noise(18);

    private SeaFloor() {
    }

    private static ImprovedNoise noise(long seed) {
        return new ImprovedNoise(new XoroshiroRandomSource(seed));
    }

    private static double fbm(ImprovedNoise n, double x, double z, double scale, int octaves) {
        double sum = 0;
        double total = 0;
        double amplitude = 1;
        double frequency = 1.0 / scale;
        for (int i = 0; i < octaves; i++) {
            sum += amplitude * n.noise(x * frequency, 0.37 * (i + 1), z * frequency);
            total += amplitude;
            amplitude *= 0.5;
            frequency *= 2;
        }
        return sum / total;
    }

    private static double smooth(double edge0, double edge1, double v) {
        double t = Mth.clamp((v - edge0) / (edge1 - edge0), 0.0, 1.0);
        return t * t * (3 - 2 * t);
    }

    private static double distanceToGridPoint(double x, double z) {
        double dx = Math.abs(Mth.positiveModulo(x - GRID_OFFSET + GRID / 2, GRID) - GRID / 2);
        double dz = Math.abs(Mth.positiveModulo(z - GRID_OFFSET + GRID / 2, GRID) - GRID / 2);
        return Math.sqrt(dx * dx + dz * dz);
    }

    /** The y of the first water block above the sea floor at this column (the floor's top block is one below). */
    public static int height(int blockX, int blockZ) {
        double flat = smooth(DOME_FLAT, DOME_BLEND, distanceToGridPoint(blockX, blockZ))
                * smooth(SPAWN_FLAT, SPAWN_BLEND, Math.sqrt((double) blockX * blockX + (double) blockZ * blockZ));
        if (flat <= 0.0) {
            return BASE;
        }
        double x = blockX + 140 * fbm(WARP_X, blockX, blockZ, 600, 2);
        double z = blockZ + 140 * fbm(WARP_Z, blockX, blockZ, 600, 2);

        double relief = fbm(PLATE, x, z, 1500, 3) * 20;

        double ridge = Mth.clamp(1 - Math.abs(fbm(RIDGE, x, z, 700, 3)) * 5, 0, 1);
        relief += ridge * ridge * 48 * smooth(-0.1, 0.3, fbm(RIDGE_MASK, x, z, 2200, 2));

        double trench = Mth.clamp(1 - Math.abs(fbm(TRENCH, x, z, 900, 2)) * 9, 0, 1);
        relief -= trench * trench * 40;

        double mount = fbm(MOUNT, x, z, 280, 2);
        relief += Math.max(0, mount - 0.3) / 0.7 * 60;

        relief += fbm(HILL, x, z, 130, 3) * 10;
        relief += fbm(DETAIL, x, z, 32, 2) * 3;

        return Mth.clamp((int) Math.round(BASE + relief * flat), MIN, MAX);
    }
}
