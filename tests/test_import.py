import volunteer_recording


def test_has_run() -> None:
    assert hasattr(volunteer_recording, "run")
    assert callable(volunteer_recording.run)
