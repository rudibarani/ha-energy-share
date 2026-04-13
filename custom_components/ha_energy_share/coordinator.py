from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import *


class EnergyShareCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.energy = {}

        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def _get(self, entity_id):
        try:
            state = self.hass.states.get(entity_id)
            return float(state.state) if state and state.state not in ["unknown", "unavailable"] else 0.0
        except:
            return 0.0

    async def _async_update_data(self):
        cfg = self.entry.data
        sources = cfg[CONF_SOURCES]
        load = self._get(cfg[CONF_LOAD])
        deadband = cfg.get(CONF_DEADBAND, DEFAULT_DEADBAND)

        if load < deadband:
            load = 0

        remaining = load
        parent_distribution = {}

        for src in cfg[CONF_PRIORITY]:
            if src not in sources:
                continue

            power = self._get(sources[src]["sensor"])

            if src == "battery" and power < 0:
                power = 0

            share = min(power, remaining)
            parent_distribution[src] = share
            remaining -= share

        if remaining > 0:
            parent_distribution["grid"] = parent_distribution.get("grid", 0) + remaining

        child_distribution = {}

        for parent, val in parent_distribution.items():
            children = sources.get(parent, {}).get("children", {})

            if not children:
                child_distribution[parent] = {parent: val}
                continue

            total_child_power = sum(self._get(e) for e in children.values())
            child_distribution[parent] = {}

            for child_name, entity in children.items():
                p = self._get(entity)
                ratio = (p / total_child_power) if total_child_power > 0 else 0
                child_distribution[parent][child_name] = val * ratio

        result = {}

        for consumer, cdata in cfg[CONF_CONSUMERS].items():
            c_power = self._get(cdata["entity"])
            factor = (c_power / load) if load > 0 else 0

            result[consumer] = {}

            for parent, children in child_distribution.items():
                allowed = cdata.get("allowed_sources", {}).get(parent, "all")

                for child, val in children.items():
                    if allowed != "all" and child not in allowed:
                        continue

                    key = f"{parent}_{child}"
                    result[consumer][key] = val * factor

        dt = UPDATE_INTERVAL / 3600

        for consumer in result:
            for src in result[consumer]:
                key = f"{consumer}_{src}"
                self.energy.setdefault(key, 0)
                self.energy[key] += result[consumer][src] * dt / 1000

        return result
