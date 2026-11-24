fill ~-2 ~ ~-2 ~3 ~4 ~3 minecraft:glass hollow
fill ~-2 ~ ~-2 ~3 ~ ~3 minecraft:sea_lantern
setworldspawn ~ ~1 ~
summon minecraft:marker ~ ~1 ~ {Tags:["packpack_pod"]}
execute store result storage packpack:start y int 1 run data get entity @e[type=minecraft:marker,tag=packpack_pod,limit=1] Pos[1]
kill @e[type=minecraft:marker,tag=packpack_pod]
data modify storage packpack:start built set value 1b
forceload remove ~ ~
