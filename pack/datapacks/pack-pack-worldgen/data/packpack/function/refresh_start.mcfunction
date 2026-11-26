execute if block -15 -13 -6 minecraft:water run setblock -15 -13 -6 minecraft:light[level=0,waterlogged=true]
execute if block -15 -13 0 minecraft:water run setblock -15 -13 0 minecraft:light[level=0,waterlogged=true]
execute if block -15 0 -6 minecraft:water run setblock -15 0 -6 minecraft:light[level=0,waterlogged=true]
execute if block -15 0 0 minecraft:water run setblock -15 0 0 minecraft:light[level=0,waterlogged=true]
execute if block 0 -13 -6 minecraft:water run setblock 0 -13 -6 minecraft:light[level=0,waterlogged=true]
execute if block 0 -13 1 minecraft:water run setblock 0 -13 1 minecraft:light[level=0,waterlogged=true]
execute if block 0 0 -6 minecraft:water run setblock 0 0 -6 minecraft:light[level=0,waterlogged=true]
execute if block 0 0 0 minecraft:water run setblock 0 0 0 minecraft:light[level=0,waterlogged=true]
schedule function packpack:refresh_start_done 5t
