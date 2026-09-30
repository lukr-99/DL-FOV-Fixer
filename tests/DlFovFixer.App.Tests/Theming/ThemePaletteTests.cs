using System.Windows.Media;
using DlFovFixer.App.Theming;
using DlFovFixer.Core.Settings;

namespace DlFovFixer.App.Tests.Theming;

/// <summary>Both palettes are complete, and their text is readable (WCAG AA, 4.5 to 1).</summary>
public sealed class ThemePaletteTests
{
    public static TheoryData<string> Palettes() => ["Light", "Dark"];

    [Theory]
    [MemberData(nameof(Palettes))]
    public void Text_IsReadableOnEverySurface(string name)
    {
        var palette = Palette(name);

        foreach (var surface in new[] { palette.Background, palette.Surface, palette.SurfaceRaised })
        {
            Assert.True(Contrast(palette.TextPrimary, surface) >= 4.5, $"{name} TextPrimary on {surface}");
            Assert.True(Contrast(palette.TextSecondary, surface) >= 4.5, $"{name} TextSecondary on {surface}");
        }
    }

    [Theory]
    [MemberData(nameof(Palettes))]
    public void OnPrimary_IsReadableOnPrimary(string name)
    {
        var palette = Palette(name);

        Assert.True(Contrast(palette.OnPrimary, palette.Primary) >= 4.5);
    }

    [Theory]
    [MemberData(nameof(Palettes))]
    public void StatusAndFocus_StandOutFromTheBackground(string name)
    {
        var palette = Palette(name);

        // WCAG's 3 to 1 for graphics and focus indicators.
        foreach (var color in new[] { palette.Danger, palette.Success, palette.Focus })
        {
            Assert.True(Contrast(color, palette.Background) >= 3, $"{name} {color}");
        }
    }

    [Fact]
    public void Palettes_SetTheSameTokens()
    {
        var light = ThemePalette.Light.Tokens().Select(token => token.Key);
        var dark = ThemePalette.Dark.Tokens().Select(token => token.Key);

        Assert.Equal(light, dark);
        Assert.Equal(11, light.Distinct().Count());
    }

    [Theory]
    [InlineData(ThemeMode.Light, true, false)]
    [InlineData(ThemeMode.Dark, false, true)]
    [InlineData(ThemeMode.System, true, true)]
    [InlineData(ThemeMode.System, false, false)]
    public void IsDarkFor_FollowsWindowsOnlyInSystemMode(ThemeMode mode, bool windowsIsDark, bool expected) =>
        Assert.Equal(expected, ThemeApplier.IsDarkFor(mode, windowsIsDark));

    private static ThemePalette Palette(string name) => name == "Dark" ? ThemePalette.Dark : ThemePalette.Light;

    private static double Contrast(Color a, Color b)
    {
        var (lighter, darker) = (Luminance(a), Luminance(b)) is var (x, y) && x > y ? (x, y) : (y, x);
        return (lighter + 0.05) / (darker + 0.05);
    }

    private static double Luminance(Color color)
    {
        static double Channel(byte value)
        {
            var c = value / 255.0;
            return c <= 0.03928 ? c / 12.92 : Math.Pow((c + 0.055) / 1.055, 2.4);
        }

        return (0.2126 * Channel(color.R)) + (0.7152 * Channel(color.G)) + (0.0722 * Channel(color.B));
    }
}
