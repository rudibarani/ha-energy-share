from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for consumer in entry.data["consumers"]:
        for parent in entry.data["sources"]:
            children = entry.data["sources"][parent].get("children", {})

            if children:
                for child in children:
                    key = f"{parent}_{child}"
                    entities.append(PowerSensor(coordinator, consumer, key))
                    entities.append(EnergySensor(coordinator, consumer, key))
            else:
                entities.append(PowerSensor(coordinator, consumer, parent))
                entities.append(EnergySensor(coordinator, consumer, parent))

    async_add_entities(entities)


class BaseSensor(SensorEntity):
    def __init__(self, coordinator, consumer, source):
        self.coordinator = coordinator
        self.consumer = consumer
        self.source = source

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.consumer)},
            name=self.consumer,
            manufacturer="HA Energy Share",
        )


class PowerSensor(BaseSensor):
    def __init__(self, coordinator, consumer, source):
        super().__init__(coordinator, consumer, source)
        self._attr_name = f"{consumer} {source.replace('_', ' ')} Power"
        self._attr_unit_of_measurement = "W"

    @property
    def native_value(self):
        return self.coordinator.data.get(self.consumer, {}).get(self.source, 0)


class EnergySensor(BaseSensor):
    def __init__(self, coordinator, consumer, source):
        super().__init__(coordinator, consumer, source)
        self._attr_name = f"{consumer} {source.replace('_', ' ')} Energy"
        self._attr_unit_of_measurement = "kWh"
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        key = f"{self.consumer}_{self.source}"
        return self.coordinator.energy.get(key, 0)
