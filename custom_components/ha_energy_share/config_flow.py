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

    # -------------------------------------------------
    # STEP 1: LOAD
    # -------------------------------------------------
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.data["load"] = user_input["load"]
            return await self.async_step_source_groups()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("load"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            })
        )

    # -------------------------------------------------
    # STEP 2: SOURCE GROUPS (z. B. renewable, grid)
    # -------------------------------------------------
    async def async_step_source_groups(self, user_input=None):
        if user_input is not None:
            name = user_input["name"]

            self.data["sources"][name] = {
                "children": {}
            }

            if not user_input["add_another"]:
                self.data["current_source_group"] = list(self.data["sources"].keys())[0]
                return await self.async_step_source_entities()

            return await self.async_step_source_groups()

        return self.async_show_form(
            step_id="source_groups",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Optional("add_another", default=True): bool
            })
        )

    # -------------------------------------------------
    # STEP 3: SOURCE ENTITIES (Kinder)
    # -------------------------------------------------
    async def async_step_source_entities(self, user_input=None):
        current = self.data["current_source_group"]

        if user_input is not None:
            if user_input.get("done"):
                keys = list(self.data["sources"].keys())
                idx = keys.index(current)

                if idx + 1 < len(keys):
                    self.data["current_source_group"] = keys[idx + 1]
                    return await self.async_step_source_entities()

                self.data.pop("current_source_group")
                return await self.async_step_consumers()

            # Nur speichern, wenn beide Felder gesetzt sind
            if user_input.get("name") and user_input.get("entity"):
                self.data["sources"][current]["children"][user_input["name"]] = user_input["entity"]

            return await self.async_step_source_entities()

        return self.async_show_form(
            step_id="source_entities",
            description_placeholders={"group": current},
            data_schema=vol.Schema({
                vol.Optional("name"): str,
                vol.Optional("entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("done", default=False): bool
            })
        )

    # -------------------------------------------------
    # STEP 4: CONSUMER GROUPS
    # -------------------------------------------------
    async def async_step_consumers(self, user_input=None):
        if user_input is not None:
            name = user_input["name"]

            self.data["consumers"][name] = {
                "children": {}
            }

            if not user_input["add_another"]:
                self.data["current_consumer_group"] = list(self.data["consumers"].keys())[0]
                return await self.async_step_consumer_entities()

            return await self.async_step_consumers()

        return self.async_show_form(
            step_id="consumers",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Optional("add_another", default=True): bool
            })
        )

    # -------------------------------------------------
    # STEP 5: CONSUMER ENTITIES
    # -------------------------------------------------
    async def async_step_consumer_entities(self, user_input=None):
        current = self.data["current_consumer_group"]

        if user_input is not None:
            if user_input.get("done"):
                keys = list(self.data["consumers"].keys())
                idx = keys.index(current)

                if idx + 1 < len(keys):
                    self.data["current_consumer_group"] = keys[idx + 1]
                    return await self.async_step_consumer_entities()

                self.data.pop("current_consumer_group")
                return await self.async_step_finish()

            if user_input.get("name") and user_input.get("entity"):
                self.data["consumers"][current]["children"][user_input["name"]] = {
                    "entity": user_input["entity"],
                    "allowed_sources": {}
                }

            return await self.async_step_consumer_entities()

        return self.async_show_form(
            step_id="consumer_entities",
            description_placeholders={"group": current},
            data_schema=vol.Schema({
                vol.Optional("name"): str,
                vol.Optional("entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("done", default=False): bool
            })
        )

    # -------------------------------------------------
    # STEP 6: PRIORITY + DEADBAND
    # -------------------------------------------------
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


# -------------------------------------------------
# OPTIONS FLOW (nachträgliche Änderung möglich)
# -------------------------------------------------
class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.data["priority"] = user_input["priority"]
            self.data["deadband"] = user_input["deadband"]
            return self.async_create_entry(title="", data=self.data)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "priority",
                    default=self.data.get("priority")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(self.data["sources"].keys()),
                        multiple=True
                    )
                ),
                vol.Optional(
                    "deadband",
                    default=self.data.get("deadband", 50)
                ): int
            })
        )
