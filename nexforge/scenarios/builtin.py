"""Built-in fault scenarios."""
import random
from .base import Scenario, Disturbance, register


@register
class MotorFailure(Scenario):
    name = "motor_failure"
    description = "Motor stalls mid-operation — current spikes, flow drops"

    def disturbances(self, duration_s):
        t = duration_s / 2
        return [
            Disturbance(at_seconds=t, channel="current_a", value=15.0, duration_s=2.0),
            Disturbance(at_seconds=t, channel="flow_lpm", value=0.0, duration_s=2.0),
        ]

    def applicable_to(self, domain):
        return domain in ("pump", "drone", "robot_arm")


@register
class SensorStuck(Scenario):
    name = "sensor_stuck"
    description = "Sensor value freezes at its current reading"

    def disturbances(self, duration_s):
        return [Disturbance(at_seconds=duration_s * 0.3,
                            channel="flow_lpm", value=5.0, duration_s=duration_s)]


@register
class Overheating(Scenario):
    name = "overheating"
    description = "Ambient temperature rises rapidly"

    def disturbances(self, duration_s):
        return [Disturbance(at_seconds=duration_s * 0.4,
                            channel="temp_c", value=95.0, duration_s=5.0)]

    def applicable_to(self, domain):
        return domain in ("pump", "cold_storage", "nuclear_reactor")


@register
class NoisySignal(Scenario):
    name = "noisy_signal"
    description = "Sensor reading corrupted with high-frequency noise"

    def disturbances(self, duration_s):
        random.seed(42)  # deterministic
        t0 = duration_s * 0.5
        # Inject noise into flow_lpm (visible in output) with short pulses
        return [
            Disturbance(at_seconds=t0 + i * 0.01,
                        channel="flow_lpm",  # ← Changed from current_a
                        value=random.uniform(-2.0, 2.0),
                        duration_s=0.01)  # ← Short pulse, not persistent
            for i in range(100)
        ]


@register
class PacketLoss(Scenario):
    name = "packet_loss"
    description = "MQTT telemetry packets dropped for a window"

    def disturbances(self, duration_s):
        return [Disturbance(at_seconds=duration_s * 0.6,
                            channel="__comm_loss__", value=1.0, duration_s=3.0)]
