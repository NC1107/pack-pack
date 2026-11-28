// The sea floor has no trees, so wood starts as kelp: smelt it in the start sub's furnace, pack
// nine dried kelp into a block, and the block works like a log. Plain oak planks keep every
// vanilla and modded recipe that wants wood working.
ServerEvents.recipes(event => {
  event.shapeless(Item.of('minecraft:oak_planks', 4), ['minecraft:dried_kelp_block']).id('packpack:kelp_planks')
})
