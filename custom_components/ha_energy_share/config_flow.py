import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN


@config_entries.HANDLERS.register(DOMAIN)
class EnergyShareConfigFlow(config_entries.ConfigFlow):
    VERSION = 1

    def __init__(self):
        self.data = {
            "sources": {},
            "consumers": {}
        }

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.data["load"] = user_input["load"]
            return await self.async_step_sources()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("load"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            })
        )

    async def async_step_sources(self, user_input=None):
        if user_input is not None:
            name = user_input["name"]

            self.data["sources"][name] = {
                "sensor": user_input["sensor"],
                "children": {}
            }

            if user_input["add_another"]:
                return await self.async_step_sources()
            return await self.async_step_children()

        return self.async_show_form(
            step_id="sources",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("add_another", default=True): bool
            })
        )

    async def async_step_children(self, user_input=None):
        if not self.data["sources"]:
            return await self.async_step_consumers()

        if "current_source" not in self.data:
            self.data["current_source"] = list(self.data["sources"].keys())[0]

        current = self.data["current_source"]

        if user_input is not None:
            if user_input.get("done"):
                keys = list(self.data["sources"].keys())
                idx = keys.index(current)

                if idx + 1 < len(keys):
                    self.data["current_source"] = keys[idx + 1]
                    return await self.async_step_children()
                else:
                    self.data.pop("current_source")
                    return await self.async_step_consumers()

            if user_input.get("name") and user_input.get("sensor"):
                self.data["sources"][current]["children"][user_input["name"]] = user_input["sensor"]

            return await self.async_step_children()

        return self.async_show_form(
            step_id="children",
            description_placeholders={"source": current},
            data_schema=vol.Schema({
                vol.Optional("name"): str,
                vol.Optional("sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("done", default=False): bool
            })
        )

    async def async_step_consumers(self, user_input=None):
        if user_input is not None:
            name = user_input["name"]

            self.data["consumers"][name] = {
                "entity": user_input["entity"],
                "allowed_sources": {}
            }

            if user_input["add_another"]:
                return await self.async_step_consumers()

            return await self.async_step_finish()

        return self.async_show_form(
            step_id="consumers",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("add_another", default=True): bool
            })
        )

    async def async_step_finish(self, user_input=None):
        if user_input is not None:
            self.data["priority"] = user_input["priority"]
            self.data["deadband"] = user_input["deadband"]

            return self.async_create_entry(
                title="HA Energy Share",
                data=self.data
            )

        return self.async_show_form(
            step_id="finish",
            data_schema=vol.Schema({
                vol.Required(
                    "priority",
                    default=list(self.data["sources"].keys())
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(self.data["sources"].keys()),
                        multiple=True
                    )
                ),
                vol.Optional("deadband", default=50): int
            })
        )
