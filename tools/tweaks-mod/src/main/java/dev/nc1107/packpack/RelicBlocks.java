package dev.nc1107.packpack;

import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.TransparentBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

/**
 * The start sub's hull and windows, made by the civilisation that built the domes and rated for the
 * deep by Deep Seas (config/submarine_hull.json). They drop nothing when broken, so the start sub
 * can't be stripped for deep-rated plating: expanding it takes plating found in the cities.
 * Very hard rather than unbreakable, because the sub has to assemble into a Sable ship later.
 */
public final class RelicBlocks {
    private static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(PackPackTweaks.MOD_ID);
    private static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(PackPackTweaks.MOD_ID);

    /** Obsidian-hard, so breaking it by accident is unlikely and on purpose is slow. */
    private static final float HARDNESS = 50.0f;
    private static final float BLAST_RESISTANCE = 1200.0f;

    public static final DeferredBlock<Block> RELIC_HULL = BLOCKS.register("relic_hull", () -> new Block(
        BlockBehaviour.Properties.of()
            .mapColor(MapColor.COLOR_BLACK)
            .strength(HARDNESS, BLAST_RESISTANCE)
            .requiresCorrectToolForDrops()
            .sound(SoundType.NETHERITE_BLOCK)
            .noLootTable()));

    public static final DeferredBlock<TransparentBlock> RELIC_GLASS = BLOCKS.register("relic_glass", () -> new TransparentBlock(
        BlockBehaviour.Properties.of()
            .mapColor(MapColor.COLOR_CYAN)
            .strength(HARDNESS, BLAST_RESISTANCE)
            .sound(SoundType.GLASS)
            .noOcclusion()
            .isValidSpawn((state, level, pos, type) -> false)
            .isRedstoneConductor((state, level, pos) -> false)
            .isSuffocating((state, level, pos) -> false)
            .isViewBlocking((state, level, pos) -> false)
            .noLootTable()));

    public static final DeferredItem<BlockItem> RELIC_HULL_ITEM = ITEMS.registerSimpleBlockItem(RELIC_HULL, new Item.Properties());
    public static final DeferredItem<BlockItem> RELIC_GLASS_ITEM = ITEMS.registerSimpleBlockItem(RELIC_GLASS, new Item.Properties());

    private RelicBlocks() {
    }

    public static void register(IEventBus modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
    }
}
