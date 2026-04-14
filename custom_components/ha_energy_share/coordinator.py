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
        load = self._get(cfg[CONF_LOAD])
        deadband = cfg.get(CONF_DEADBAND, DEFAULT_DEADBAND)

        if load < deadband:
            load = 0

        # -----------------------------------
        # 1. Quellen summieren (Parent-Level)
        # -----------------------------------
        parent_power = {}
        for group, gdata in cfg[CONF_SOURCES].items():
            total = 0
            for entity in gdata["children"].values():
                total += self._get(entity)
            parent_power[group] = total

        # -----------------------------------
        # 2. Verteilung (Priorität)
        # -----------------------------------
        remaining = load
        parent_distribution = {}

        for src in cfg[CONF_PRIORITY]:
            power = parent_power.get(src, 0)

            if src == "battery" and power < 0:
                power = 0

            share = min(power, remaining)
            parent_distribution[src] = share
            remaining -= share

        if remaining > 0:
            parent_distribution["grid"] = parent_distribution.get("grid", 0) + remaining

        # -----------------------------------
        # 3. Child-Aufteilung
        # -----------------------------------
        child_distribution = {}

        for parent, val in parent_distribution.items():
            children = cfg[CONF_SOURCES].get(parent, {}).get("children", {})

            if not children:
                child_distribution[parent] = {parent: val}
                continue

            total = sum(self._get(e) for e in children.values())
            child_distribution[parent] = {}

            for name, entity in children.items():
                p = self._get(entity)
                ratio = (p / total) if total > 0 else 0
                child_distribution[parent][name] = val * ratio

        # -----------------------------------
        # 4. Verbraucher-Verteilung
        # -----------------------------------
        result = {}

        for group, gdata in cfg[CONF_CONSUMERS].items():
            for name, cdata in gdata["children"].items():

                power = self._get(cdata["entity"])
                factor = (power / load) if load > 0 else 0

                key_consumer = f"{group}_{name}"
                result[key_consumer] = {}

                for parent, children in child_distribution.items():
                    for child, val in children.items():
                        key = f"{parent}_{child}"
                        result[key_consumer][key] = val * factor

        # -----------------------------------
        # 5. Gruppensummen bilden
        # -----------------------------------
        group_totals = {}

        for group, gdata in cfg[CONF_CONSUMERS].items():
            group_totals[group] = {}

            for name in gdata["children"]:
                consumer_key = f"{group}_{name}"

                for src, val in result.get(consumer_key, {}).items():
                    group_totals[group].setdefault(src, 0)
                    group_totals[group][src] += val

        # zusammenführen
        result.update(group_totals)

        # -----------------------------------
        # 6. Energieintegration
        # -----------------------------------
        dt = UPDATE_INTERVAL / 3600

        for consumer in result:
            for src in result[consumer]:
                key = f"{consumer}_{src}"
                self.energy.setdefault(key, 0)
                self.energy[key] += result[consumer][src] * dt / 1000

        return result
