execute unless data storage packpack:start built run forceload add -16 -16 16 16
execute unless data storage packpack:start built positioned 0 -13 0 if loaded -17 0 -17 if loaded -17 0 17 if loaded 17 0 -17 if loaded 17 0 17 run function packpack:build_start
execute if data storage packpack:start built as @a[tag=!packpack_started] run function packpack:place_new_player with storage packpack:start
