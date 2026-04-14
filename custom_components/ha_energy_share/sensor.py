from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    consumers = entry.data["consumers"]
    sources = entry.data["sources"]

    # Einzelverbraucher
    for group, gdata in consumers.items():
        for name in gdata["children"]:
            consumer_key = f"{group}_{name}"

            for parent in sources:
                children = sources[parent]["children"]

                if children:
                    for child in children:
                        src_key = f"{parent}_{child}"
                        entities.append(PowerSensor(coordinator, consumer_key, src_key))
                        entities.append(EnergySensor(coordinator, consumer_key, src_key))
                else:
                    entities.append(PowerSensor(coordinator, consumer_key, parent))
                    entities.append(EnergySensor(coordinator, consumer_key, parent))

    # Gruppensummen
    for group in consumers:
        for parent in sources:
            children = sources[parent]["children"]

            if children:
                for child in children:
                    src_key = f"{parent}_{child}"
                    entities.append(PowerSensor(coordinator, group, src_key))
                    entities.append(EnergySensor(coordinator, group, src_key))
            else:
                entities.append(PowerSensor(coordinator, group, parent))
                entities.append(EnergySensor(coordinator, group, parent))

    async_add_entities(entities)


class BaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, consumer, source):
        super().__init__(coordinator)
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
        self._attr_name = f"{consumer} {source} Power"
        self._attr_unit_of_measurement = "W"

    @property
    def native_value(self):
        return self.coordinator.data.get(self.consumer, {}).get(self.source, 0)


class EnergySensor(BaseSensor):
    def __init__(self, coordinator, consumer, source):
        super().__init__(coordinator, consumer, source)
        self._attr_name = f"{consumer} {source} Energy"
        self._attr_unit_of_measurement = "kWh"
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        key = f"{self.consumer}_{self.source}"
        return self.coordinator.energy.get(key, 0)
