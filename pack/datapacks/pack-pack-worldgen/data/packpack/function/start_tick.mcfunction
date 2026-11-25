execute unless data storage packpack:start built run forceload add -8 -8 8 8
execute unless data storage packpack:start built positioned 0 -13 0 if loaded -9 0 -9 if loaded -9 0 9 if loaded 9 0 -9 if loaded 9 0 9 run function packpack:build_start_dome
execute if data storage packpack:start built as @a[tag=!packpack_started] run function packpack:place_new_player with storage packpack:start
