using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace DlFovFixer.App.Shell;

/// <summary>
/// Draws the tray icon: a field-of-view cone opening from a lens, on a dark rounded tile. The shape
/// never changes and the color shows the status, as in 1.0. The result is a whole .ico file with one
/// frame per tray size, so Windows picks the sharpest one for the screen's scale.
/// </summary>
public static class StatusIconFactory
{
    /// <summary>The frame sizes: the tray at 100% to 400% scale, and the larger Explorer views.</summary>
    public static IReadOnlyList<int> Sizes { get; } = [16, 20, 24, 32, 40, 48, 64];

    private static readonly Color Tile = Color.FromRgb(26, 22, 17);
    private static readonly Color Lens = Color.FromRgb(18, 15, 11);

    // Coordinates are fractions of the icon's size, fitted to 1.0's Pillow drawing.
    private const double Margin = 0.05;
    private const double CornerRadius = 0.26;
    private const double BorderWidth = 0.06;
    private const double ApexX = 0.5;
    private const double ApexY = 0.82;
    private const double ConeRadius = 0.60;
    private const double HalfAngle = 45;
    private const double RayWidth = 0.013;
    private const double ArcWidth = 0.022;
    private const double LensRadius = 0.08;

    /// <summary>The bytes of a .ico file for <paramref name="color"/>. Must run on an STA thread.</summary>
    public static byte[] CreateIcon(StatusColor color)
    {
        var frames = Sizes.Select(size => (size, pixels: Render(size, color))).ToList();
        using var stream = new MemoryStream();
        using var writer = new BinaryWriter(stream);

        // ICONDIR, then one ICONDIRENTRY per frame, then the frames as 32-bit DIBs.
        writer.Write((short)0);
        writer.Write((short)1);
        writer.Write((short)frames.Count);
        var offset = 6 + (16 * frames.Count);
        foreach (var (size, _) in frames)
        {
            var length = DibLength(size);
            writer.Write((byte)size);
            writer.Write((byte)size);
            writer.Write((byte)0);
            writer.Write((byte)0);
            writer.Write((short)1);
            writer.Write((short)32);
            writer.Write(length);
            writer.Write(offset);
            offset += length;
        }

        foreach (var (size, pixels) in frames)
        {
            WriteDib(writer, size, pixels);
        }

        writer.Flush();
        return stream.ToArray();
    }

    /// <summary>Premultiplied BGRA pixels, top row first.</summary>
    internal static byte[] Render(int size, StatusColor color)
    {
        var (bright, deep) = Palette(color);
        var visual = new DrawingVisual();
        using (var context = visual.RenderOpen())
        {
            context.PushTransform(new ScaleTransform(size, size));

            var border = new Pen(new SolidColorBrush(bright), BorderWidth);
            var inset = Margin + (BorderWidth / 2);
            context.DrawRoundedRectangle(
                new SolidColorBrush(Tile),
                border,
                new Rect(inset, inset, 1 - (2 * inset), 1 - (2 * inset)),
                CornerRadius - (BorderWidth / 2),
                CornerRadius - (BorderWidth / 2));

            var apex = new Point(ApexX, ApexY);
            context.DrawGeometry(new SolidColorBrush(bright), null, Cone(apex, ConeRadius));

            var rayPen = new Pen(new SolidColorBrush(deep), RayWidth);
            foreach (var offset in new[] { -HalfAngle + 6, -HalfAngle / 2, 0, HalfAngle / 2, HalfAngle - 6 })
            {
                context.DrawLine(rayPen, apex, PointAt(apex, ConeRadius * 0.94, offset));
            }

            context.DrawGeometry(null, new Pen(new SolidColorBrush(deep), ArcWidth), Arc(apex, ConeRadius * 0.56));
            context.DrawEllipse(new SolidColorBrush(Lens), new Pen(new SolidColorBrush(bright), ArcWidth), apex, LensRadius, LensRadius);
        }

        var bitmap = new RenderTargetBitmap(size, size, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(visual);
        var pixels = new byte[size * size * 4];
        bitmap.CopyPixels(pixels, size * 4, 0);
        return pixels;
    }

    private static (Color Bright, Color Deep) Palette(StatusColor color) => color switch
    {
        StatusColor.Green => (Color.FromRgb(74, 200, 110), Color.FromRgb(26, 120, 60)),
        StatusColor.Red => (Color.FromRgb(235, 72, 72), Color.FromRgb(140, 30, 30)),
        _ => (Color.FromRgb(240, 170, 60), Color.FromRgb(150, 96, 20)),
    };

    /// <summary>A point <paramref name="radius"/> away from the apex, <paramref name="degrees"/> off straight up.</summary>
    private static Point PointAt(Point apex, double radius, double degrees)
    {
        var angle = (degrees - 90) * Math.PI / 180;
        return new Point(apex.X + (radius * Math.Cos(angle)), apex.Y + (radius * Math.Sin(angle)));
    }

    private static StreamGeometry Cone(Point apex, double radius)
    {
        var geometry = new StreamGeometry();
        using (var context = geometry.Open())
        {
            context.BeginFigure(apex, isFilled: true, isClosed: true);
            context.LineTo(PointAt(apex, radius, -HalfAngle), isStroked: false, isSmoothJoin: false);
            context.ArcTo(PointAt(apex, radius, HalfAngle), new Size(radius, radius), 0, false, SweepDirection.Clockwise, false, false);
        }

        geometry.Freeze();
        return geometry;
    }

    private static StreamGeometry Arc(Point apex, double radius)
    {
        var geometry = new StreamGeometry();
        using (var context = geometry.Open())
        {
            context.BeginFigure(PointAt(apex, radius, -HalfAngle), isFilled: false, isClosed: false);
            context.ArcTo(PointAt(apex, radius, HalfAngle), new Size(radius, radius), 0, false, SweepDirection.Clockwise, true, false);
        }

        geometry.Freeze();
        return geometry;
    }

    // BITMAPINFOHEADER, the pixels, and a 1-bit AND mask whose rows are padded to 4 bytes.
    private static int DibLength(int size) => 40 + (size * size * 4) + (MaskStride(size) * size);

    private static int MaskStride(int size) => ((size + 31) / 32) * 4;

    private static void WriteDib(BinaryWriter writer, int size, byte[] premultiplied)
    {
        writer.Write(40);
        writer.Write(size);
        writer.Write(size * 2);
        writer.Write((short)1);
        writer.Write((short)32);
        writer.Write(0);
        writer.Write(size * size * 4);
        writer.Write(0);
        writer.Write(0);
        writer.Write(0);
        writer.Write(0);

        // Icons store straight alpha, bottom row first.
        for (var y = size - 1; y >= 0; y--)
        {
            for (var x = 0; x < size; x++)
            {
                var i = ((y * size) + x) * 4;
                var alpha = premultiplied[i + 3];
                for (var channel = 0; channel < 3; channel++)
                {
                    var value = premultiplied[i + channel];
                    writer.Write(alpha == 0 ? (byte)0 : (byte)Math.Min(255, (value * 255 + (alpha / 2)) / alpha));
                }

                writer.Write(alpha);
            }
        }

        writer.Write(new byte[MaskStride(size) * size]);
    }
}
