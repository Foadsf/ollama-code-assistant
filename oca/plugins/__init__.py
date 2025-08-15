# This directory will contain the plugin system for OCA.
# Plugins can be used to extend OCA's functionality with new commands,
# tools, or language support.

# The plugin system might look for classes inheriting from a `BasePlugin`
# and register them automatically.
#
# Example:
#
# class BasePlugin:
#     name: str
#     description: str
#
#     def register(self, oca_instance):
#         raise NotImplementedError
#
# A plugin file `my_plugin.py` in this directory could define:
#
# class MyAwesomePlugin(BasePlugin):
#     name = "awesome"
#     description = "Adds an awesome new command."
#
#     def register(self, oca_instance):
#         oca_instance.register_command("awesome", self.awesome_command)
#
#     def awesome_command(self, ...):
#         print("Awesome command executed!")
