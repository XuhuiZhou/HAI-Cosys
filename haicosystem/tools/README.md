The tools registration and definition are inherited from [ToolEmu](https://toolemu.com/).

To add a new tool, you need to:
1. Implement the tool class
2. Register the tool class using the `@register_toolkit` decorator
We additionally implement the output parser class:
3. Implement the output parser class
4. Register the output parser class using the `@register_output_parser` decorator

We also added other new tools following the same convention.

The Mypy errors are due
