fill ~0 ~0 ~0 ~10 ~4 ~4 minecraft:waxed_cut_copper hollow
setblock ~3 ~2 ~0 create_submarine:iron_pressurizer
setblock ~5 ~2 ~0 create_submarine:iron_pressurizer
setblock ~8 ~2 ~0 create_submarine:iron_pressurizer
setblock ~2 ~2 ~4 create_submarine:iron_pressurizer
setblock ~8 ~2 ~4 create_submarine:iron_pressurizer
setblock ~10 ~2 ~2 create_submarine:iron_pressurizer
setblock ~3 ~2 ~2 create:creative_motor[facing=west]{ScrollValue:256}
setblock ~2 ~2 ~2 create:clutch[axis=x,powered=true]
setblock ~2 ~3 ~2 minecraft:lever[face=floor,facing=north,powered=true]
setblock ~1 ~2 ~2 create:gearshift[axis=x,powered=false]
setblock ~1 ~3 ~2 minecraft:lever[face=floor,facing=north,powered=false]
setblock ~0 ~2 ~2 create:andesite_encased_shaft[axis=x]
setblock ~-1 ~2 ~2 create_submarine:submarine_propeller[facing=west,reversed=false]
setblock ~6 ~0 ~2 create_submarine:ballast_vent
setblock ~6 ~1 ~2 create_submarine:pump_controller[facing=up]
setblock ~6 ~2 ~2 create_submarine:ballast_tank
setblock ~6 ~3 ~2 create_submarine:ballast_tank
setblock ~2 ~1 ~1 create_submarine:ballast_tank
setblock ~2 ~1 ~3 create_submarine:ballast_tank
setblock ~8 ~3 ~1 create_submarine:ballast_tank
setblock ~8 ~3 ~3 create_submarine:ballast_tank
setblock ~7 ~1 ~2 create:cogwheel[axis=y]
setblock ~7 ~2 ~2 create:creative_motor[facing=down]{ScrollValue:256}
setblock ~4 ~1 ~1 create_submarine:command_sub[facing=south]
setblock ~9 ~1 ~1 create_submarine:creative_oxygenator
setblock ~4 ~1 ~4 minecraft:iron_door[facing=north,hinge=left,open=false,powered=false,half=lower]
setblock ~4 ~2 ~4 minecraft:iron_door[facing=north,hinge=left,open=false,powered=false,half=upper]
setblock ~5 ~2 ~3 minecraft:stone_button[face=wall,facing=north]
setblock ~5 ~2 ~5 minecraft:stone_button[face=wall,facing=south]
fill ~-2 ~-1 ~-1 ~11 ~5 ~5 minecraft:air replace minecraft:water
tp @s ~5 ~1 ~2
sable assemble area ~-2 ~-1 ~-1 ~11 ~5 ~5
fill ~-2 ~-1 ~-1 ~11 ~5 ~5 minecraft:water replace minecraft:air
tellraw @s ["",{"text":"You are inside the test sub. ","color":"aqua"},"At the stern, the lever on the clutch starts and stops the propeller and the one on the gearshift reverses it. Use the Onboard Computer screen to set a depth and it fills and drains the ballast to get there. The shaft through the hull holds to about 68 m."]
