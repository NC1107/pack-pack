fill ~0 ~0 ~0 ~10 ~4 ~4 minecraft:iron_block hollow
setblock ~3 ~2 ~2 create:creative_motor[facing=west]
setblock ~2 ~2 ~2 create:clutch[axis=x,powered=true]
setblock ~2 ~3 ~2 minecraft:lever[face=floor,facing=north,powered=true]
setblock ~1 ~2 ~2 create:shaft[axis=x]
setblock ~0 ~2 ~2 create:andesite_encased_shaft[axis=x]
setblock ~-1 ~2 ~2 create_submarine:submarine_propeller[facing=west,reversed=false]
setblock ~6 ~0 ~2 create_submarine:ballast_vent
setblock ~6 ~1 ~2 create:mechanical_pump[facing=up]
setblock ~6 ~2 ~2 create_submarine:ballast_tank
setblock ~6 ~3 ~2 create_submarine:ballast_tank
setblock ~9 ~1 ~2 create:creative_motor[facing=west]
setblock ~8 ~1 ~2 create:clutch[axis=x,powered=true]
setblock ~8 ~2 ~2 minecraft:lever[face=floor,facing=north,powered=true]
setblock ~7 ~1 ~2 create:gearshift[axis=x,powered=false]
setblock ~7 ~2 ~2 minecraft:lever[face=floor,facing=north,powered=false]
setblock ~9 ~1 ~1 create_submarine:creative_oxygenator
setblock ~4 ~1 ~4 minecraft:oak_door[facing=south,hinge=left,open=false,powered=false,half=lower]
setblock ~4 ~2 ~4 minecraft:oak_door[facing=south,hinge=left,open=false,powered=false,half=upper]
sable assemble area ~-2 ~-1 ~-1 ~11 ~5 ~5
tellraw @s ["",{"text":"Test sub built above you at the surface. ","color":"aqua"},"Inside: lever on the stern clutch starts the propeller, lever on the middle clutch runs the ballast pump, lever on the gearshift next to it switches between diving and rising."]
