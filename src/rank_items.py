__all__ = [
    "beet_default",
]


from dataclasses import InitVar, dataclass, field
from typing import Iterable, Dict, List
from beet.library.data_pack import Function

import yaml

from beet import Context, DataPack, ResourcePack
from beet.core.utils import extra_field
from lectern import Document, Fragment


length_score = "#spectral_necrosis.name_length lepsen.lvar"

categories: Iterable[str] = None


@dataclass(frozen=True)
class RankedItem:
    id: str
    rank: int
    category: str


@dataclass
class ItemCategories:
    trident: Iterable[RankedItem] = ()
    mainhand: Iterable[RankedItem] = ()
    offhand: Iterable[RankedItem] = ()
    boots: Iterable[RankedItem] = ()
    leggings: Iterable[RankedItem] = ()
    chestplate: Iterable[RankedItem] = ()
    helmet: Iterable[RankedItem] = ()

    min_length: int = extra_field(init=False, default=None)
    max_length: int = extra_field(init=False, default=None)
    by_length: Dict[int, List[RankedItem]] = extra_field(
        init=False, default_factory=dict
    )

    @classmethod
    def load(cls, fragment: str) -> "ItemCategories":
        parsed = yaml.safe_load(fragment)
        kwargs = {}
        for category in categories:
            if items := parsed.get(category):
                items = [RankedItem(k, items[k], category) for k in items]
                kwargs[category] = tuple(items)
        return cls(**kwargs)

    def __post_init__(self):
        for category in categories:
            for item in getattr(self, category):
                length = len("minecraft:") + len(item.id)
                if self.min_length is None or length < self.min_length:
                    self.min_length = length
                if self.max_length is None or length > self.max_length:
                    self.max_length = length
                if length not in self.by_length:
                    self.by_length[length] = []
                self.by_length[length].append(item)
        self.by_length = {k: self.by_length[k] for k in sorted(self.by_length)}


categories = ItemCategories.__init__.__code__.co_varnames[1:]


@dataclass
class ItemFunction:
    item: RankedItem
    check_matched: InitVar[bool]
    name: str = field(init=False)
    command: str = field(init=False)
    content: str = field(
        init=False,
        default=(
            "# Indicate that the item was successfully ranked and categorized.\n"
            "scoreboard players set #spectral_necrosis.matched lepsen.lvar 1\n\n"
        ),
    )

    def __post_init__(self, check_matched: bool):
        item_id = f"minecraft:{self.item.id}"
        category = self.item.category
        rank = self.item.rank
        item_check = (
            "if data storage spectral_necrosis:data items.current{"
            f'id:"minecraft:{self.item.id}"'
            "}"
        )
        if check_matched:
            item_check = (
                "if score #spectral_necrosis.matched lepsen.lvar matches 0 "
                + item_check
            )
        self.name = f"spectral_necrosis:rank/{category}/{rank}"
        self.command = f"execute {item_check} run function {self.name}"
        if rank > 0:
            rank *= 10_000
            self.content += (
                "# Calculate the item rank based on its tier and durability.\n"
                "execute store result score #spectral_necrosis.damage lepsen.lvar run "
                "data get storage spectral_necrosis:data items.current.Damage\n"
                f"scoreboard players set #spectral_necrosis.rank lepsen.lvar {rank}\n"
                "scoreboard players operation #spectral_necrosis.rank lepsen.lvar -= "
                "#spectral_necrosis.damage lepsen.lvar\n\n"
            )
            best_check = (
                f"execute if score #spectral_necrosis.best_{category} lepsen.lvar < "
                "#spectral_necrosis.rank lepsen.lvar run"
            )
            self.content += (
                "# If this item is the best in its category, queue it to be equipped.\n"
                f"{best_check} data modify storage spectral_necrosis:data items.{category} "
                "set from storage spectral_necrosis:data items.current\n"
                f"{best_check} scoreboard players operation "
                f"#spectral_necrosis.best_{category} lepsen.lvar = "
                "#spectral_necrosis.rank lepsen.lvar\n"
            )
            if category == "trident":
                self.content += "function spectral_necrosis:rank/mainhand/0\n"
        else:
            best_check = f"execute if score #spectral_necrosis.best_{category} lepsen.lvar matches -1 run"
            self.content += (
                f"# Equip this item in the {category} slot if there is nothing better to wear.\n"
                f"{best_check} data modify storage spectral_necrosis:data items.{category} "
                "set from storage spectral_necrosis:data items.current\n"
                f"{best_check} scoreboard players set "
                f"#spectral_necrosis.best_{category} lepsen.lvar 0\n"
            )


def beet_default(ctx: Context):
    def directive(fragment: Fragment, assets: ResourcePack, data: DataPack):
        items = ItemCategories.load(fragment.content)
        by_length = items.by_length
        keys = tuple(by_length.keys())
        interval = len(keys) // 4
        rem = len(keys) % 4
        indices = []
        for i in range(0, 4):
            x = indices[i - 1][1] if i > 0 else 0
            y = x + interval
            if i < rem:
                y += 1
            indices.append((x, y))
        chunks = [[(k, by_length[k]) for k in keys[i:j]] for i, j in indices]
        item_tree = []
        for chunk in chunks:
            begin, end = chunk[0][0], chunk[-1][0]
            range_check = f"if score {length_score} matches {begin}..{end}"
            range_function = f"spectral_necrosis:rank/by_length/{begin}-{end}"
            range_contents = (
                "# This function ranks items with IDs from "
                f"{begin} to {end} characters long.\n"
            )
            for length, items in chunk:
                length_check = f"if score {length_score} matches {length}"
                length_function = f"spectral_necrosis:rank/by_length/{length}"
                length_contents = (
                    f"# This function ranks items with {length}-character long IDs.\n"
                )
                for i, item in enumerate(items):
                    item_function = ItemFunction(item, i > 0)
                    data.functions[item_function.name] = Function(item_function.content)
                    length_contents += item_function.command + "\n"
                data.functions[length_function] = Function(length_contents)
                range_contents += (
                    f"execute {length_check} run function {length_function}\n"
                )
            data.functions[range_function] = Function(range_contents)
            item_tree.append(f"execute {range_check} run function {range_function}")
        mainhand_0 = ItemFunction(RankedItem("", 0, "mainhand"), False)
        data.functions[mainhand_0.name] = Function(mainhand_0.content)

        ctx.template.env.globals["item_tree"] = "\n".join(item_tree)

    document = ctx.inject(Document)
    document.directives["item_ranks"] = directive
