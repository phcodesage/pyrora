# Plugins

Plugins are explicit service providers, never automatically imported from the
environment. Call `app.install(MyPlugin())` during application setup.

`register(app)` can add container services, routes, middleware, commands,
event listeners, template/static directories, config defaults, and health
checks. `async boot(app)` runs once at ASGI startup.

Declare `name`, semantic `version`, `dependencies`, and `config_defaults`.
Dependencies must already be installed; duplicates produce a `PluginError`.
`pyrora plugins discover` lists `pyrora.plugins` entry points without importing
them. This protects applications from arbitrary installed-package code.

The local `examples/plugin` provider demonstrates every registration surface.
