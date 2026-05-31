from nexforge.runtime.events import EventBus, Event, Priority


def test_priority_ordering():
    bus = EventBus()
    received = []
    bus.subscribe("x", lambda e: received.append(e.priority), Priority.NORMAL)
    bus.publish(Event("x", None, Priority.LOW, 1))
    bus.publish(Event("x", None, Priority.CRITICAL, 2))
    bus.publish(Event("x", None, Priority.NORMAL, 3))
    bus.drain()
    assert received == [Priority.CRITICAL, Priority.NORMAL, Priority.LOW]


def test_bounded_queue_drops():
    bus = EventBus(capacities={Priority.LOW: 2, Priority.NORMAL: 2,
                                Priority.HIGH: 2, Priority.CRITICAL: 2})
    ok1 = bus.publish_now("x", 1, Priority.LOW)
    ok2 = bus.publish_now("x", 2, Priority.LOW)
    ok3 = bus.publish_now("x", 3, Priority.LOW)
    assert ok1 and ok2 and not ok3
    stats = bus.stats()
    assert stats["LOW"]["dropped"] == 1
