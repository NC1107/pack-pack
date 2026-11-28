execute if block -14 -13 -14 minecraft:water run setblock -14 -13 -14 minecraft:light[level=0,waterlogged=true]
execute if block -14 -13 0 minecraft:water run setblock -14 -13 0 minecraft:light[level=0,waterlogged=true]
execute if block -14 -13 16 minecraft:water run setblock -14 -13 16 minecraft:light[level=0,waterlogged=true]
execute if block 0 -13 -14 minecraft:water run setblock 0 -13 -14 minecraft:light[level=0,waterlogged=true]
execute if block 0 -13 9 minecraft:water run setblock 0 -13 9 minecraft:light[level=0,waterlogged=true]
execute if block 0 -13 16 minecraft:water run setblock 0 -13 16 minecraft:light[level=0,waterlogged=true]
schedule function packpack:refresh_start_done 5t
