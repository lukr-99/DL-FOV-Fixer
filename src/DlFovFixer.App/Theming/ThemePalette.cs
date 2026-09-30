using System.Windows.Media;

namespace DlFovFixer.App.Theming;

/// <summary>
/// The app's semantic colors for one mode (CodePrint's theme contract). Views read them through
/// <see cref="ThemeTokens"/> keys, never as literal colors, so a switch applies at once. The accent
/// is separate from the neutral surfaces, and the status colors match the tray icon's.
/// </summary>
public sealed record ThemePalette(
    Color Background,
    Color Surface,
    Color SurfaceRaised,
    Color TextPrimary,
    Color TextSecondary,
    Color Border,
    Color Primary,
    Color OnPrimary,
    Color Danger,
    Color Success,
    Color Focus)
{
    public static ThemePalette Light { get; } = new(
        Background: Color.FromRgb(0xF7, 0xF5, 0xF2),
        Surface: Color.FromRgb(0xFF, 0xFF, 0xFF),
        SurfaceRaised: Color.FromRgb(0xFF, 0xFF, 0xFF),
        TextPrimary: Color.FromRgb(0x1A, 0x16, 0x11),
        TextSecondary: Color.FromRgb(0x5C, 0x55, 0x4C),
        Border: Color.FromRgb(0xD6, 0xD0, 0xC7),
        Primary: Color.FromRgb(0x8A, 0x57, 0x0C),
        OnPrimary: Color.FromRgb(0xFF, 0xFF, 0xFF),
        Danger: Color.FromRgb(0xB0, 0x2A, 0x2A),
        Success: Color.FromRgb(0x1A, 0x78, 0x3C),
        Focus: Color.FromRgb(0x8A, 0x57, 0x0C));

    public static ThemePalette Dark { get; } = new(
        Background: Color.FromRgb(0x1A, 0x16, 0x11),
        Surface: Color.FromRgb(0x24, 0x1F, 0x19),
        SurfaceRaised: Color.FromRgb(0x2E, 0x28, 0x21),
        TextPrimary: Color.FromRgb(0xF2, 0xEE, 0xE8),
        TextSecondary: Color.FromRgb(0xB8, 0xB0, 0xA5),
        Border: Color.FromRgb(0x45, 0x3D, 0x33),
        Primary: Color.FromRgb(0xF0, 0xAA, 0x3C),
        OnPrimary: Color.FromRgb(0x1A, 0x16, 0x11),
        Danger: Color.FromRgb(0xEB, 0x48, 0x48),
        Success: Color.FromRgb(0x4A, 0xC8, 0x6E),
        Focus: Color.FromRgb(0xF0, 0xAA, 0x3C));

    /// <summary>Every color with its token key, for applying and for checking contrast.</summary>
    public IEnumerable<(string Key, Color Color)> Tokens()
    {
        yield return (ThemeTokens.Background, Background);
        yield return (ThemeTokens.Surface, Surface);
        yield return (ThemeTokens.SurfaceRaised, SurfaceRaised);
        yield return (ThemeTokens.TextPrimary, TextPrimary);
        yield return (ThemeTokens.TextSecondary, TextSecondary);
        yield return (ThemeTokens.Border, Border);
        yield return (ThemeTokens.Primary, Primary);
        yield return (ThemeTokens.OnPrimary, OnPrimary);
        yield return (ThemeTokens.Danger, Danger);
        yield return (ThemeTokens.Success, Success);
        yield return (ThemeTokens.Focus, Focus);
    }
}
