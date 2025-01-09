from typing import List

from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.constants import ALIGN_TOP_CENTER
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen


def create_styled_subtitles(
    lyric_screens: List[LyricsScreen],
    resolution,
    fontsize,
) -> ASS:
    a = ASS()
    a.set_resolution(resolution)

    a.styles_format = [
        "Name",  # The name of the Style. Case sensitive. Cannot include commas.
        "Fontname",  # The fontname as used by Windows. Case-sensitive.
        "Fontsize",  # Font size
        "PrimaryColour",  # This is the colour that a subtitle will normally appear in.
        "SecondaryColour",  # This colour may be used instead of the Primary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
        "OutlineColour",  # This colour may be used instead of the Primary or Secondary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
        "BackColour",  # This is the colour of the subtitle outline or shadow, if these are used
        "Bold",  # This defines whether text is bold (true) or not (false). -1 is True, 0 is False
        "Italic",  # This defines whether text is italic (true) or not (false). -1 is True, 0 is False
        "Underline",  # [-1 or 0]
        "StrikeOut",  # [-1 or 0]
        "ScaleX",  # Modifies the width of the font. [percent]
        "ScaleY",  # Modifies the height of the font. [percent]
        "Spacing",  # Extra space between characters. [pixels]
        "Angle",  # The origin of the rotation is defined by the alignment. Can be a floating point number. [degrees]
        "BorderStyle",  # 1=Outline + drop shadow, 3=Opaque box
        "Outline",  # If BorderStyle is 1,  then this specifies the width of the outline around the text, in pixels. Values may be 0, 1, 2, 3 or 4.
        "Shadow",  # If BorderStyle is 1,  then this specifies the depth of the drop shadow behind the text, in pixels. Values may be 0, 1, 2, 3 or 4. Drop shadow is always used in addition to an outline - SSA will force an outline of 1 pixel if no outline width is given.
        "Alignment",  # This sets how text is "justified" within the Left/Right onscreen margins, and also the vertical placing. Values may be 1=Left, 2=Centered, 3=Right. Add 4 to the value for a "Toptitle". Add 8 to the value for a "Midtitle". eg. 5 = left-justified toptitle
        "MarginL",  # This defines the Left Margin in pixels. It is the distance from the left-hand edge of the screen.The three onscreen margins (MarginL, MarginR, MarginV) define areas in which the subtitle text will be displayed.
        "MarginR",  # This defines the Right Margin in pixels. It is the distance from the right-hand edge of the screen.
        "MarginV",  # MarginV. This defines the vertical Left Margin in pixels. For a subtitle, it is the distance from the bottom of the screen. For a toptitle, it is the distance from the top of the screen. For a midtitle, the value is ignored - the text will be vertically centred
        "Encoding",  #
    ]

    style = Style()
    style.type = "Style"
    style.Name = "Nomad"
    style.Fontname = "Avenir Next Bold"
    style.Fontsize = fontsize

    style.PrimaryColour = (112, 112, 247, 255)
    style.SecondaryColour = (255, 255, 255, 255)
    style.OutlineColour = (26, 58, 235, 255)
    style.BackColour = (0, 255, 0, 255)  # (26, 58, 235, 255)

    style.Bold = False
    style.Italic = False
    style.Underline = False
    style.StrikeOut = False

    style.ScaleX = 100
    style.ScaleY = 100
    style.Spacing = 0
    style.Angle = 0.0
    style.BorderStyle = 1
    style.Outline = 1
    style.Shadow = 0
    style.Alignment = ALIGN_TOP_CENTER
    style.MarginL = 0
    style.MarginR = 0
    style.MarginV = 0
    style.Encoding = 0

    a.add_style(style)

    a.events_format = ["Layer", "Style", "Start", "End", "MarginV", "Text"]
    for screen in lyric_screens:
        [a.add(event) for event in screen.as_ass_events(style)]

    return a
