execute as @e[type=minecraft:villager,tag=packpack_new_villager] at @s if block ~ ~ ~ minecraft:water run kill @s
tag @e[type=minecraft:villager,tag=packpack_new_villager] remove packpack_new_villager
