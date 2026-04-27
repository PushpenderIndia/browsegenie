"""Tests for ScreenshotRecorder and ScreenshotFrame."""

from browsegenie.core.browser_agent.playback.recorder import ScreenshotFrame, ScreenshotRecorder


class TestScreenshotFrame:
    """Test cases for the ScreenshotFrame dataclass."""

    def test_creation(self):
        """Test that ScreenshotFrame stores all provided fields and auto-sets timestamp."""
        f = ScreenshotFrame(index=0, step=1, tool="click", url="https://x.com", title="X", image_b64="abc")
        assert f.index == 0
        assert f.step == 1
        assert f.tool == "click"
        assert f.url == "https://x.com"
        assert f.title == "X"
        assert f.image_b64 == "abc"
        assert f.timestamp > 0

    def test_to_dict(self):
        """Test that to_dict serialises all fields including image as the 'image' key."""
        f = ScreenshotFrame(index=2, step=3, tool="navigate", url="https://a.com", title="A", image_b64="data")
        d = f.to_dict()
        assert d["index"] == 2
        assert d["step"] == 3
        assert d["tool"] == "navigate"
        assert d["url"] == "https://a.com"
        assert d["title"] == "A"
        assert d["image"] == "data"
        assert "timestamp" in d


class TestScreenshotRecorder:
    """Test cases for the ScreenshotRecorder class."""

    def setup_method(self):
        """Set up a fresh ScreenshotRecorder for each test."""
        self.recorder = ScreenshotRecorder()

    def test_initially_empty(self):
        """Test that a new recorder has zero frames and returns empty collections."""
        assert self.recorder.count() == 0
        assert self.recorder.to_list() == []
        assert self.recorder.frames == []

    def test_record_single_frame(self):
        """Test that recording one frame returns a ScreenshotFrame with index 0."""
        frame = self.recorder.record(step=1, tool="click", url="https://x.com", title="X", image_b64="b64data")
        assert isinstance(frame, ScreenshotFrame)
        assert frame.index == 0
        assert self.recorder.count() == 1

    def test_record_multiple_frames_index_increments(self):
        """Test that sequential recordings assign incrementing index values."""
        self.recorder.record(1, "click", "https://a.com", "A", "img1")
        self.recorder.record(2, "fill", "https://b.com", "B", "img2")
        self.recorder.record(3, "navigate", "https://c.com", "C", "img3")
        assert self.recorder.count() == 3

        frames = self.recorder.frames
        assert frames[0].index == 0
        assert frames[1].index == 1
        assert frames[2].index == 2

    def test_get_by_index(self):
        """Test that get() retrieves a frame by its numeric index."""
        self.recorder.record(1, "click", "https://x.com", "X", "img")
        frame = self.recorder.get(0)
        assert frame is not None
        assert frame.step == 1

    def test_get_out_of_range_returns_none(self):
        """Test that get() returns None for an index beyond the current frame count."""
        assert self.recorder.get(0) is None
        assert self.recorder.get(-1) is None
        assert self.recorder.get(100) is None

    def test_get_negative_index_returns_none(self):
        """Test that get() returns None for a negative index even when frames exist."""
        self.recorder.record(1, "click", "https://x.com", "X", "img")
        assert self.recorder.get(-1) is None

    def test_to_list_returns_dicts(self):
        """Test that to_list returns a list of serialised frame dicts in insertion order."""
        self.recorder.record(1, "click", "https://x.com", "X", "img1")
        self.recorder.record(2, "fill", "https://y.com", "Y", "img2")
        lst = self.recorder.to_list()
        assert len(lst) == 2
        assert all(isinstance(item, dict) for item in lst)
        assert lst[0]["tool"] == "click"
        assert lst[1]["tool"] == "fill"

    def test_frames_property_returns_copy(self):
        """Test that mutating the list returned by frames does not affect the recorder's internal state."""
        self.recorder.record(1, "click", "https://x.com", "X", "img")
        frames = self.recorder.frames
        frames.clear()
        assert self.recorder.count() == 1
