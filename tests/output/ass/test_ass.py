import pytest
from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.style import Style


class TestASS:
    @pytest.fixture
    def ass(self):
        """Create a basic ASS instance for testing"""
        return ASS()

    @pytest.fixture
    def sample_style(self):
        """Create a sample style for testing"""
        style = Style()
        style.Name = "Default"
        style.Fontname = "Arial"
        style.Fontsize = 20
        style.PrimaryColour = "&H00FFFFFF"
        style.SecondaryColour = "&H000000FF"
        style.OutlineColour = "&H00000000"
        style.BackColour = "&H00000000"
        style.Bold = 0
        style.Italic = 0
        style.Underline = 0
        style.StrikeOut = 0
        style.ScaleX = 100
        style.ScaleY = 100
        style.Spacing = 0
        style.Angle = 0
        style.BorderStyle = 1
        style.Outline = 2
        style.Shadow = 2
        style.Alignment = 2
        style.MarginL = 10
        style.MarginR = 10
        style.MarginV = 10
        return style

    @pytest.fixture
    def sample_event(self, sample_style):
        """Create a sample dialogue event for testing"""
        event = Event()
        event.type = "Dialogue"
        event.Layer = 0
        event.Start = 0.0
        event.End = 5.0
        event.Style = sample_style
        event.Name = ""
        event.MarginL = 0
        event.MarginR = 0
        event.MarginV = 0
        event.Effect = ""
        event.Text = "Test subtitle"
        return event

    def test_add_event(self, ass, sample_event):
        """Test adding an event"""
        ass.add(sample_event)
        assert len(ass.events) == 1
        assert ass.events[0] == sample_event

    def test_add_style(self, ass, sample_style):
        """Test adding a style"""
        ass.add_style(sample_style)
        assert len(ass.styles) == 1
        assert ass.styles[0] == sample_style

    def test_parse_text_basic(self, ass):
        """Test basic text parsing without formatting"""
        text = "Plain text"
        result = ass.parse_text(text)
        assert result == text

    def test_parse_text_with_tags(self, ass):
        """Test parsing text with formatting tags"""
        text = r"{\b1}Bold{\b0} text"
        result = ass.parse_text(text, modify_tag_block=lambda b: "")
        assert result == "Bold text"

    def test_shiftscale_time(self, ass, sample_event):
        """Test time scaling of events"""
        ass.add(sample_event)
        ass.shiftscale(time_scale=2.0)
        assert ass.events[0].Start == 0.0
        assert ass.events[0].End == 10.0

    def test_resolution(self, ass):
        """Test setting and getting resolution"""
        ass.set_resolution((1280, 720))
        assert ass.resolution() == (1280, 720)

    def test_split_line(self, ass, sample_event):
        """Test splitting a line at a given time"""
        ass.add(sample_event)
        split_time = 2.5
        original_start = sample_event.Start  # 0.0
        original_end = sample_event.End  # 5.0

        # The __range_cut method will split at both start and end times if provided
        ass.shiftscale(split=True, start=split_time, end=original_end)

        # We expect two events after splitting at split_time:
        # 1. Original event from 0.0 to split_time
        # 2. New event from split_time to 5.0
        assert len(ass.events) == 2

        # Find the earlier and later events
        first_event = min(ass.events, key=lambda e: e.Start)
        second_event = max(ass.events, key=lambda e: e.Start)

        # First part should go from original start to split point
        assert first_event.Start == original_start
        assert first_event.End == split_time

        # Second part should go from split point to original end
        assert second_event.Start == split_time
        assert second_event.End == original_end

    def test_remove_formatting(self, ass):
        """Test removing formatting from text"""
        text = r"{\b1}Bold{\b0} and {\i1}italic{\i0}"
        event = Event()
        event.Text = text
        event.Style = Style()
        ass.add(event)

        ass.remove_formatting(tags=True)
        assert ass.events[0].Text == "Bold and italic"

    def test_tidy_styles(self, ass):
        """Test tidying styles"""
        style1 = Style()
        style2 = Style()

        style1.Name = "Default"
        style2.Name = "Default2"

        for style in [style1, style2]:
            style.Fontname = "Arial"
            style.Fontsize = 20
            style.PrimaryColour = "&H00FFFFFF"
            style.SecondaryColour = "&H000000FF"
            style.OutlineColour = "&H00000000"
            style.BackColour = "&H00000000"
            style.Bold = 0
            style.Italic = 0
            style.Underline = 0
            style.StrikeOut = 0
            style.ScaleX = 100
            style.ScaleY = 100
            style.Spacing = 0
            style.Angle = 0
            style.BorderStyle = 1
            style.Outline = 2
            style.Shadow = 2
            style.Alignment = 2
            style.MarginL = 10
            style.MarginR = 10
            style.MarginV = 10

        ass.add_style(style1)
        ass.add_style(style2)

        event1 = Event()
        event1.Style = style1
        event2 = Event()
        event2.Style = style2
        ass.add(event1)
        ass.add(event2)

        ass.tidy_styles(combine=True, identical=True)
        assert any(s.Name in ["Default", "Default2"] for s in ass.styles)

    def test_merge(self, ass, sample_event):
        """Test merging two ASS objects"""
        other = ASS()
        other.add(sample_event)

        ass.merge(other=other, time_offset=1.0)
        assert len(ass.events) == 1
        assert ass.events[0].Start == 1.0
        assert ass.events[0].End == 6.0

    def test_loop_single_point(self, ass, sample_event, sample_style):
        """Test looping a single point in time"""
        # Ensure event has proper style and timing
        sample_event.Style = sample_style
        sample_event.Start = 0.0
        sample_event.End = 5.0
        sample_event.Text = "Test subtitle"
        ass.add(sample_event)

        loop_point = 2.5
        loop_length = 3.0

        ass.loop(time=loop_point, length=loop_length)

        # The loop method should:
        # 1. Split the original event at loop_point (2.5)
        # 2. Create a new event of length loop_length (3.0) starting at loop_point
        # 3. Adjust timings of events after loop_point

        assert len(ass.events) == 3  # Original split into two + new looped section

        # Sort events by start time for easier verification
        sorted_events = sorted(ass.events, key=lambda e: e.Start)

        # First part: 0.0 to loop_point
        assert sorted_events[0].Start == 0.0
        assert sorted_events[0].End == loop_point

        # Second part: loop_point to loop_point + loop_length
        assert sorted_events[1].Start == loop_point
        assert sorted_events[1].End == loop_point + loop_length

        # Third part: Original end shifted by loop_length
        assert sorted_events[2].Start >= loop_point + loop_length
        assert sorted_events[2].End == 5.0 + loop_length

    def test_loop_range(self, ass, sample_event):
        """Test looping a time range"""
        ass.add(sample_event)
        start_time = 1.0
        end_time = 3.0
        count = 2

        ass.loop(start=start_time, end=end_time, count=count)

        # Verify we have the expected number of events
        assert len(ass.events) >= count
        # Verify timing is maintained
        for event in ass.events:
            assert event.Start < event.End

    def test_write_srt_basic(self, ass, sample_event, sample_style, tmp_path):
        """Test basic SRT file writing"""
        # Ensure event has proper style and timing
        sample_event.Style = sample_style
        sample_event.Text = "Test subtitle"
        sample_event.type = "Dialogue"
        ass.add(sample_event)

        output_file = tmp_path / "test.srt"
        ass.write_srt(str(output_file))

        # Verify file exists and contains basic SRT format
        assert output_file.exists()
        content = output_file.read_text()
        assert "1" in content  # subtitle number
        assert "-->" in content  # timestamp separator
        assert "Test subtitle" in content

    def test_write_srt_with_overlap(self, ass, sample_style, tmp_path):
        """Test SRT writing with overlapping subtitles"""
        event1 = Event()
        event1.Style = sample_style
        event1.type = "Dialogue"
        event1.Start = 0.0
        event1.End = 2.0
        event1.Text = "First line"

        event2 = Event()
        event2.Style = sample_style
        event2.type = "Dialogue"
        event2.Start = 1.0
        event2.End = 3.0
        event2.Text = "Second line"

        ass.add(event1)
        ass.add(event2)

        output_file = tmp_path / "test_overlap.srt"
        ass.write_srt(str(output_file), overlap=True)

        content = output_file.read_text()
        assert "First line" in content
        assert "Second line" in content

    def test_write_srt_with_identical_lines(self, ass, sample_style, tmp_path):
        """Test SRT writing with identical sequential lines"""
        event1 = Event()
        event1.Style = sample_style
        event1.type = "Dialogue"
        event1.Start = 0.0
        event1.End = 2.0
        event1.Text = "Same text"

        event2 = Event()
        event2.Style = sample_style
        event2.type = "Dialogue"
        event2.Start = 2.0  # Immediately after event1
        event2.End = 4.0
        event2.Text = "Same text"

        ass.add(event1)
        ass.add(event2)

        output_file = tmp_path / "test_identical.srt"
        ass.write_srt(str(output_file), join=True)

        content = output_file.read_text()
        # Should be joined into one subtitle spanning 0.0 to 4.0
        assert content.count("Same text") == 1

    def test_extract_range(self, ass, sample_event):
        """Test extracting a range of events"""
        ass.add(sample_event)
        start_time = 1.0
        end_time = 4.0

        # Create a new ASS object to extract into
        other_ass = ASS()
        ass.extract(start=start_time, end=end_time, other=other_ass, remove=False)

        # Original should be unchanged
        assert len(ass.events) == 1
        # Other should have the extracted events
        assert len(other_ass.events) > 0

    def test_shiftscale_geometry(self, ass, sample_event):
        """Test scaling geometry in an event"""
        sample_event.Text = r"{\pos(100,100)}Test"
        ass.add(sample_event)

        # Scale by 2x
        scale = (2.0, 2.0)
        ass.shiftscale(geometry_scale=scale)

        # Position should be scaled
        assert r"{\pos(200,200)}" in ass.events[0].Text

    def test_shiftscale_geometry_with_multiple_tags(self, ass, sample_event):
        """Test scaling geometry with multiple formatting tags"""
        sample_event.Text = r"{\pos(100,100)\fs20\bord2}Test"
        ass.add(sample_event)

        # Scale by 1.5x
        scale = (1.5, 1.5)
        ass.shiftscale(geometry_scale=scale)

        # Check that position, font size, and border are all scaled
        event_text = ass.events[0].Text
        assert r"{\pos(150,150)" in event_text
        assert r"\fs30" in event_text
        assert r"\bord3" in event_text
