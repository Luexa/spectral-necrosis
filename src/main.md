# Undead Players

## Version Resolution

<details>

`@function_tag(merge) load:load`
```yaml
values:
  - "#spectral_necrosis:load"
```

`@function_tag(merge) spectral_necrosis:dependencies`
```yaml
values:
  - id: "#lepsen:core/load"
    required: false
```

`@function_tag(merge) spectral_necrosis:load`
```yaml
values:
  - id: "#spectral_necrosis:dependencies"
    required: false
  - "#spectral_necrosis:enumerate"
  - "#spectral_necrosis:resolve"
```

`@function spectral_necrosis:enumerate`
```mcfunction
#!tag "spectral_necrosis:enumerate"
# Store version 0.1.0 in scoreboards unless a newer version is also loaded.
execute
    unless score spectral_necrosis.major load.status matches 0..
    run scoreboard players set spectral_necrosis.major load.status 0
execute
    if score spectral_necrosis.major load.status matches 0
    unless score spectral_necrosis.minor load.status matches 1..
    run scoreboard players set spectral_necrosis.minor load.status 1
execute
    if score spectral_necrosis.major load.status matches 0
    if score spectral_necrosis.minor load.status matches 1
    unless score spectral_necrosis.patch load.status matches 0..
    run scoreboard players set spectral_necrosis.patch load.status 0
```

`@function spectral_necrosis:resolve`
```mcfunction
#!tag "spectral_necrosis:resolve"
# Clear scheduled tick function in case pack fails to load.
schedule clear spectral_necrosis:tick

# Attempt to load the version if it matches.
execute
    if score spectral_necrosis.major load.status matches 0
    if score spectral_necrosis.minor load.status matches 1
    if score spectral_necrosis.patch load.status matches 0
    run function spectral_necrosis:try_init
```

`@function spectral_necrosis:try_init`
```mcfunction
# Store result of dependency version check in temporary scoreboard.
scoreboard players set #spectral_necrosis load.status 0
execute
    if score #lepsen_core.compat load.status matches 1
    if data storage lepsen:core compat{
        objectives: 1,
        tick_scheduler: 1
    }
    run scoreboard players set #spectral_necrosis load.status 1

# If dependencies were loaded correctly, initialize the data pack.
execute if score #spectral_necrosis load.status matches 1
    run function spectral_necrosis:init

# If the dependency failed to load, clean up scoreboards.
execute if score #spectral_necrosis load.status matches 0
    run function spectral_necrosis:fail_init

# Clear the temporary scoreboard.
scoreboard players reset #spectral_necrosis load.status
```

`@function spectral_necrosis:fail_init`
```mcfunction
# Reset fake players so other packs do not think this pack is loaded.
scoreboard players reset spectral_necrosis.major load.status
scoreboard players reset spectral_necrosis.minor load.status
scoreboard players reset spectral_necrosis.patch load.status
```

</details>

## Pack Initialization

<details>

`@function spectral_necrosis:init`
```mcfunction
# Scoreboard objective to track undead player drowned conversion.
scoreboard objectives add lue.unpl.drown dummy

# Scoreboard objective to track player deaths.
scoreboard objectives add lue.unpl.deaths minecraft.custom:minecraft.deaths
scoreboard players reset * lue.unpl.deaths

# Calculate tick offset to wait before scheduling the slow tick function.
execute unless score spectral_necrosis.tick lepsen.lvar matches 0..15
    run scoreboard players set spectral_necrosis.tick lepsen.lvar 0
scoreboard players operation #tick_diff lepsen.lvar = spectral_necrosis.tick lepsen.lvar
scoreboard players operation #tick_diff lepsen.lvar -= lepsen.current_tick lepsen.pvar
execute if score #tick_diff lepsen.lvar matches ..-1
    run scoreboard players add #tick_diff lepsen.lvar 16

# Schedule the slow tick function based on the calculated tick offset.
#!for i in range(16)
#!set j = (i + 1) ~ "t"
execute if score #tick_diff lepsen.lvar matches __i__
    run schedule function spectral_necrosis:slow_tick __j__
#!endfor

# Schedule the fast tick function to occur immediately.
schedule function spectral_necrosis:tick 1t
```

</details>

## Spawn Undead Player

<details>

`@advancement spectral_necrosis:death`
```yaml
# Run this function the instant the player dies.
rewards:
  function: spectral_necrosis:death

# Damage + deaths stat = player died.
criteria:
  death:
    # Triggers on *any* damage, not just entity.
    trigger: minecraft:entity_hurt_player
    conditions:
      player:
        # Player death is processed before this advancement trigger is activated,
        # so we can detect if the damage dealt was a fatal blow by tracking the
        # value of a scoreboard objective tracking the death count statistic.
        - condition: minecraft:entity_scores
          entity: this
          scores:
            lue.unpl.deaths: 1

        # Do not execute reward function if the pack failed to load properly.
        - condition: minecraft:value_check
          value:
            type: minecraft:score
            target:
              type: minecraft:fixed
              name: spectral_necrosis.major
            score: load.status
          range: 0
        - condition: minecraft:value_check
          value:
            type: minecraft:score
            target:
              type: minecraft:fixed
              name: spectral_necrosis.minor
            score: load.status
          range: 1
        - condition: minecraft:value_check
          value:
            type: minecraft:score
            target:
              type: minecraft:fixed
              name: spectral_necrosis.patch
            score: load.status
          range: 0
```

`@function spectral_necrosis:death`
```mcfunction
# Allow this function to be called next time the player dies.
scoreboard players reset @s lue.unpl.deaths
advancement revoke @s only spectral_necrosis:death

# Allow other packs to disable undead player spawning by setting the score
# `spectral_necrosis.disable lepsen.lvar` when this function tag is called.
function #spectral_necrosis:death_check

# Summon and initialize the undead player.
execute unless score spectral_necrosis.disable lepsen.lvar matches 1
    if entity @s[gamemode=!creative,gamemode=!spectator]
    run summon minecraft:zombie ~ ~ ~ {
        Tags: [
            spectral_necrosis.undead,
            spectral_necrosis.new,
            global.ignore.modify
        ],
        ArmorDropChances: [-300f, -300f, -300f, -300f],
        HandDropChances: [-300f, -300f],
        PersistenceRequired: 1b,
        CustomNameVisible: 1b,
        DeathLootTable: "minecraft:empty"
    }
scoreboard players reset spectral_necrosis.disable lepsen.lvar

# Generate player skull to access the dead player's name.
loot replace entity @e[type=minecraft:zombie,tag=spectral_necrosis.new,distance=0,limit=1]
    armor.head loot lepsen:core/player_head

# Initialize the undead player and its inventory.
execute as @e[type=minecraft:zombie,tag=spectral_necrosis.new,distance=0,limit=1]
    run function spectral_necrosis:undead/initialize_zombie
```

`@function spectral_necrosis:undead/initialize_zombie`
```mcfunction
# This tag is only used to call this function, so it should be immediately removed.
tag @s remove spectral_necrosis.new

# Set undead player health to 1024 so it will not die naturally.
attribute @s minecraft:generic.max_health base set 1024
data modify storage spectral_necrosis:data zombie_data set value
    {
        Health: 1024f,
        HandItems: [{}, {}],
        ArmorItems: [{}, {}, {}, {}]
    }

# Generate a custom attribute to store the player's name within the entity.
data modify storage spectral_necrosis:data name_attribute
    set value {
        UUID: __name_attribute_tag__,
        Amount: 0d,
        Operation: 0
    }
data modify storage spectral_necrosis:data name_attribute.Name
    set from entity @s ArmorItems[3].tag.SkullOwner.Name

# Process the player name to produce a string in the format of "Undead PlayerName".
item modify entity @s armor.head spectral_necrosis:zombie_name
data modify storage spectral_necrosis:data zombie_data.CustomName
    set from entity @s ArmorItems[3].tag.display.Name

# Add the custom attribute to the undead player.
data modify entity @s
    Attributes[{
        Name: "minecraft:generic.movement_speed"
    }].Modifiers
    append from storage spectral_necrosis:data name_attribute
data remove storage spectral_necrosis:data name_attribute

# Initialize item ranking trackers with sentinel vlaues.
scoreboard players set #spectral_necrosis.best_trident lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_mainhand lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_offhand lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_boots lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_leggings lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_chestplate lepsen.lvar -1
scoreboard players set #spectral_necrosis.best_helmet lepsen.lvar -1

# Attempt to rank any nearby items that spawned this tick. The items must be in
# one of the possible death positions (varies based on crawling/sneaking).
data remove storage spectral_necrosis:data items
execute as @e[type=minecraft:item,dx=0,dy=0.32,dz=0,nbt={Age:0s}]
    run function spectral_necrosis:rank/start

# Equip items set aside during the item categorization process.
data modify storage spectral_necrosis:data zombie_data.HandItems[0]
    merge from storage spectral_necrosis:data items.mainhand
data modify storage spectral_necrosis:data zombie_data.HandItems[1]
    merge from storage spectral_necrosis:data items.offhand
data modify storage spectral_necrosis:data zombie_data.ArmorItems[0]
    merge from storage spectral_necrosis:data items.boots
data modify storage spectral_necrosis:data zombie_data.ArmorItems[1]
    merge from storage spectral_necrosis:data items.leggings
data modify storage spectral_necrosis:data zombie_data.ArmorItems[2]
    merge from storage spectral_necrosis:data items.chestplate
data modify storage spectral_necrosis:data zombie_data.ArmorItems[3]
    merge from storage spectral_necrosis:data items.helmet

# Add a placeholder item to the boots slot if the zombie does not have any boots.
execute unless data storage spectral_necrosis:data zombie_data.ArmorItems[0].id
    run data modify storage spectral_necrosis:data zombie_data.ArmorItems[0]
        merge value {id: "minecraft:rotten_flesh", Count: 1b}

# If the player had a trident, set it aside so the undead player can equip it
# in the case that it becomes a drowned.
execute if data storage spectral_necrosis:data items.trident
    run data modify storage spectral_necrosis:data
        zombie_data.ArmorItems[0].tag.spectral_necrosis.trident
        set from storage spectral_necrosis:data items.trident

# Merge the generated zombie NBT with the undead player.
data modify entity @s {} merge from storage spectral_necrosis:data zombie_data
data remove storage spectral_necrosis:data zombie_data
data remove storage spectral_necrosis:data items
```

`@item_modifier spectral_necrosis:zombie_name`
```yaml
function: minecraft:set_name
entity: this
name:
  translate: "Undead %s{{ translate_ns_1 }}"
  with:
    - storage: spectral_necrosis:data
      nbt: name_attribute.Name
```

</details>

## Item Ranking

<details>

`@function spectral_necrosis:rank/start`
```mcfunction
# Items spawn at specific postions relative to the player depending on if the
# player was standing, in a vehicle, sneaking, crawling, or swimming. These
# checks ensure that item ranking is only performed if the item is in the
# exact required position, since the dx/dy/dz check is not precise enough.
#!for i in (1.32, 0.97, 0.1)
execute positioned ~ ~__i__ ~ if entity @s[distance=..0.00001]
    run function spectral_necrosis:rank/main
#!endfor
```

`@function spectral_necrosis:rank/main`
```mcfunction
# Kill the item so it cannot be duplicated.
kill @s

# This value will be set to 1 if the function tree succeeds in categorizing this item.
scoreboard players set #spectral_necrosis.matched lepsen.lvar 0

# Append item to undead player's inventory and store ID length in a fake player.
data modify storage spectral_necrosis:data items.current set from entity @s Item
execute store result score #spectral_necrosis.name_length lepsen.lvar
    run data get storage spectral_necrosis:data items.current.id

# Minimize NBT checks by dispatching item ranking process over item ID length.
__item_tree__

# If the function tree did not find a category for this item, it may be placed
# in the zombie's mainhand slot if there are no other candidates.
execute if score #spectral_necrosis.matched lepsen.lvar matches 0
    if score #spectral_necrosis.best_mainhand lepsen.lvar matches -1
    run function spectral_necrosis:rank/mainhand/0

# Add this item to the undead player's inventory.
data modify storage spectral_necrosis:data
    zombie_data.ArmorItems[0].tag.spectral_necrosis.inventory
    append from storage spectral_necrosis:data items.current
```

`@item_ranks`
```yaml
trident:
  trident: 1
mainhand:
  wooden_sword: 1
  golden_sword: 1
  stone_sword: 2
  iron_sword: 3
  diamond_sword: 4
  netherite_sword: 5
offhand:
  shield: 0
boots:
  leather_boots: 1
  golden_boots: 1
  chainmail_boots: 1
  iron_boots: 2
  diamond_boots: 3
  netherite_boots: 4
leggings:
  leather_leggings: 1
  golden_leggings: 2
  chainmail_leggings: 3
  iron_leggings: 4
  diamond_leggings: 5
  netherite_leggings: 6
chestplate:
  elytra: 0
  leather_chestplate: 1
  golden_chestplate: 2
  chainmail_chestplate: 2
  iron_chestplate: 3
  diamond_chestplate: 4
  netherite_chestplate: 5
helmet:
  carved_pumpkin: 0
  player_head: 0
  skeleton_skull: 0
  wither_skeleton_skull: 0
  zombie_head: 0
  creeper_head: 0
  dragon_head: 0
  leather_helmet: 1
  golden_helmet: 2
  chainmail_helmet: 2
  iron_helmet: 2
  turtle_helmet: 2
  diamond_helmet: 3
  netherite_helmet: 4
```

</details>

## Undead Player Drops

<details>

`@function spectral_necrosis:tick`
```mcfunction
# Schedule this function to execute every tick.
schedule function spectral_necrosis:tick 1t

# Check if undead player health drops below 1004 (e.g. it has lost 20 health,
# which would be enough to kill a normal zombie). We process death manually so
# we can expand the inventory being held by the zombie.
execute as @e[type=minecraft:zombie,tag=spectral_necrosis.undead]
    run function spectral_necrosis:drop_items/check
execute as @e[type=minecraft:drowned,tag=spectral_necrosis.undead]
    run function spectral_necrosis:drop_items/check
```

`@function spectral_necrosis:drop_items/check`
```mcfunction
# Undead player max health is 1024; check if it reaches 1004 health or below, in
# which case it should die and drop its inventory.
execute store result score #health lepsen.lvar
    run data get entity @s Health 10000
execute if score #health lepsen.lvar matches ..10040000
    run function spectral_necrosis:drop_items/main
```

`@function spectral_necrosis:drop_items/main`
```mcfunction
# Kill the undead player as the player has dealt enough damage for it to die.
kill @s

# Copy the undead player's inventory into storage, then drop each item one by one.
data modify storage spectral_necrosis:data inventory
    set from entity @s ArmorItems[0].tag.spectral_necrosis.inventory
execute at @s run function spectral_necrosis:drop_items/loop
data remove storage spectral_necrosis:data inventory
```

`@function spectral_necrosis:drop_items/loop`
```mcfunction
# Summon an item with randomized motion via `/loot spawn`.
loot spawn ~ ~ ~ loot spectral_necrosis:base_item

# Replace the spawned item with an item from the undead player's inventory.
data modify entity
    @e[type=minecraft:item,nbt={
        Item: {
            tag: {
                spectral_necrosis: {
                    base_item:1b
                }
            }
        }
    },limit=1] Item
    set from storage spectral_necrosis:data inventory[-1]

# Move on to the next item in the inventory.
data remove storage spectral_necrosis:data inventory[-1]
execute if data storage spectral_necrosis:data inventory[-1]
    run function spectral_necrosis:drop_items/loop
```

`@loot_table spectral_necrosis:base_item`
```yaml
type: minecraft:generic
pools:
  - rolls: 1
    entries:
      - type: minecraft:item
        name: minecraft:stone_button
        functions:
          - function: minecraft:set_nbt
            tag: "{spectral_necrosis:{base_item:1b}}"
```

</details>

## Drowned Conversion

<details>

`@function spectral_necrosis:slow_tick`
```mcfunction
# Schedule this function to execute every 16 ticks.
schedule function spectral_necrosis:slow_tick 16t

# Process custom undead player drowning.
execute as @e[type=minecraft:zombie,tag=spectral_necrosis.undead]
    run function spectral_necrosis:drown/check_conversion
```

`@function spectral_necrosis:drown/check_conversion`
```mcfunction
# Process drowned conversion manually so we can apply custom logic to it.
execute store result score #spectral_necrosis.conversion_time lepsen.lvar
    run data get entity @s DrownedConversionTime
execute if score #spectral_necrosis.conversion_time lepsen.lvar matches 0..
    run function spectral_necrosis:drown/update_conversion
```

`@function spectral_necrosis:drown/update_conversion`
```mcfunction
# Drowned conversion takes (15s * 20t/s) so it is our starting point.
execute unless score @s lue.unpl.drown = @s lue.unpl.drown
    run scoreboard players set @s lue.unpl.drown 300

# Calculate how much the zombie has drowned since the last call to this function.
scoreboard players set #spectral_necrosis.conversion_diff lepsen.lvar 300
scoreboard players operation #spectral_necrosis.conversion_diff lepsen.lvar -= #spectral_necrosis.conversion_time lepsen.lvar
scoreboard players operation @s lue.unpl.drown -= #spectral_necrosis.conversion_diff lepsen.lvar

# Reset the zombie's DrownedConversionTime so it doesn't drown naturally.
execute if score @s lue.unpl.drown matches 0..
    run data modify entity @s DrownedConversionTime set value 300

# The conversion is now complete; spawn a new drowned and copy the zombie's data.
execute if score @s lue.unpl.drown matches ..-1 at @s
    run function spectral_necrosis:drown/finish_drowning
```

`@function spectral_necrosis:drown/finish_drowning`
```mcfunction
# Copy the zombie's NBT to storage, then kill the zombie.
data modify storage spectral_necrosis:data zombie_data set from entity @s
data merge entity @s {Health:0f,DeathTime:19s}

# Summon the drowned and initialize it based on the contents of storage.
summon minecraft:drowned ~ ~ ~
    {
        Tags: [
            spectral_necrosis.undead,
            spectral_necrosis.new,
            global.ignore.modify
        ],
        ArmorDropChances: [-300f, -300f, -300f, -300f],
        HandDropChances: [-300f, -300f],
        PersistenceRequired: 1b,
        CustomNameVisible: 1b,
        DeathLootTable: "minecraft:empty"
    }
execute as @e[type=minecraft:drowned,tag=spectral_necrosis.new,limit=1,distance=0]
    run function spectral_necrosis:drown/initialize_drowned

# Clear storage to avoid deep comparison when this function is next called.
data remove storage spectral_necrosis:data zombie_data
```

`@function spectral_necrosis:drown/initialize_drowned`
```mcfunction
# This tag is only used to call this function, so it should be immediately removed.
tag @s remove spectral_necrosis.new

# Set drowned max health to 1024 so we can simulate death instead of allowing the
# entity to die naturally which would cause issues when dropping its items.
attribute @s minecraft:generic.max_health base set 1024
data modify storage spectral_necrosis:data drowned_data set value {Health:1024f}

# Generate name for entity ("Drowned PlayerName") based on a string form of the
# player name hidden inside of an attribute modifier.
data modify storage spectral_necrosis:data name_attribute
    set from storage spectral_necrosis:data zombie_data.Attributes[{
        Name: "minecraft:generic.movement_speed"
    }].Modifiers[{
        UUID: __name_attribute_tag__
    }]
loot replace entity @s armor.head
    loot spectral_necrosis:drowned_name
data modify storage spectral_necrosis:data drowned_data.CustomName
    set from entity @s ArmorItems[3].tag.display.Name

# Copy other tags from zombie to drowned.
data modify storage spectral_necrosis:data drowned_data.ArmorItems
    set from storage spectral_necrosis:data zombie_data.ArmorItems
data modify storage spectral_necrosis:data drowned_data.HandItems
    set from storage spectral_necrosis:data zombie_data.HandItems
    
# If the zombie had a trident, the drowned should use it as a weapon.
execute if data storage spectral_necrosis:data
    zombie_data.ArmorItems[0].tag.spectral_necrosis.trident
    run data modify storage spectral_necrosis:data drowned_data.HandItems[0]
        set from storage spectral_necrosis:data
        zombie_data.ArmorItems[0].tag.spectral_necrosis.trident

# Copy player name attribute from zombie to drowned.
data modify entity @s
    Attributes[{
        Name: "minecraft:generic.movement_speed"
    }].Modifiers
    append from storage spectral_necrosis:data name_attribute
data remove storage spectral_necrosis:data name_attribute

# Update the drowned based on the contents of storage.
data modify entity @s {} merge from storage spectral_necrosis:data drowned_data
data remove storage spectral_necrosis:data drowned_data
```

`@loot_table spectral_necrosis:drowned_name`
```yaml
type: minecraft:generic
pools:
  - rolls: 1
    entries:
      - type: minecraft:item
        name: minecraft:bow
        functions:
          - function: minecraft:set_name
            entity: this
            name:
              translate: "Drowned %s{{ translate_ns_1 }}"
              with:
                - storage: spectral_necrosis:data
                  nbt: name_attribute.Name
```

</details>

## Peaceful Mode

<details>

`@function spectral_necrosis:check/peaceful_mode`
```mcfunction
#!tag "spectral_necrosis:death_check"
# Disable undead player spawning if the world's difficulty is Peaceful.
execute store result score #spectral_necrosis.difficulty lepsen.lvar run difficulty
execute if score #spectral_necrosis.difficulty lepsen.lvar matches 0
    run scoreboard players set spectral_necrosis.disable lepsen.lvar 1
```

</details>
