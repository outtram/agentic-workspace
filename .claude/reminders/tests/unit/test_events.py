from reminders.core.events import Event, WorkItemCreated, EventBus

def test_event_creation():
    """Should create event with timestamp"""
    event = WorkItemCreated(work_item_id="OUT-264", reminder_id=None)

    assert event.work_item_id == "OUT-264"
    assert event.reminder_id is None
    assert event.timestamp is not None

def test_event_bus_subscribe_and_publish():
    """Should call handler when event published"""
    bus = EventBus()
    called = []

    def handler(event):
        called.append(event)

    bus.subscribe(WorkItemCreated, handler)
    event = WorkItemCreated(work_item_id="OUT-264")
    bus.publish(event)

    assert len(called) == 1
    assert called[0].work_item_id == "OUT-264"

def test_event_bus_multiple_subscribers():
    """Should call all subscribers for event type"""
    bus = EventBus()
    calls = {"handler1": 0, "handler2": 0}

    def handler1(event):
        calls["handler1"] += 1

    def handler2(event):
        calls["handler2"] += 1

    bus.subscribe(WorkItemCreated, handler1)
    bus.subscribe(WorkItemCreated, handler2)
    bus.publish(WorkItemCreated(work_item_id="OUT-264"))

    assert calls["handler1"] == 1
    assert calls["handler2"] == 1
