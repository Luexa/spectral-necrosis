[Download the latest release]: https://github.com/Luewd/spectral-necrosis/releases/latest
[releases page]: https://github.com/Luewd/spectral-necrosis/releases/latest
[Beet]: https://github.com/mcbeet/beet
[Lectern]: https://github.com/mcbeet/lectern
[Poetry]: https://pypi.org/project/poetry/
[MIT License]: LICENSE
[`pyproject.toml`]: pyproject.toml

# Spectral Necrosis

Spectral Necrosis is a Minecraft data pack that causes dead players to become zombies that protect the contents of the player's inventory.

[Download the latest release].

## Development

Spectral Necrosis uses the [Beet] and [Lectern] toolchains for ease of development and enhanced maintainability.
As such, the pack must be built with the help of some Python packages before it can be included in your world.

Please refer to the [releases page] if you are an ordinary user.

```sh
# If you do not already have Poetry, please run `pip install poetry`.
git clone https://github.com/Luewd/spectral-necrosis
cd spectral-necrosis
poetry install
poetry run beet build
```

Beet configuration is declared inline, under `[tool.beet]` in [`pyproject.toml`].

## License

Spectral Necrosis is made freely available under the terms of the [MIT License].
Third-party contributions shall be licensed under the same terms unless explicitly stated otherwise.
