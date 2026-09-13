using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using Map_Editor.Engine;
using Map_Editor.Engine.Map;
using Map_Editor.Engine.Terrain;
using Map_Editor.Engine.Tools;
using Map_Editor.Engine.Types;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;

// Standalone x86 regression harness. All writes go into a unique temporary directory.
class MovementTests
{
    static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
    static string root;
    static Heightmaps terrain;
    static Heightmaps.Heightmap Add(int x, int y)
    {
        Heightmaps.Heightmap block = new Heightmaps.Heightmap(null);
        block.HeightFile = new HIM { FilePath = Path.Combine(root, x + "_" + y + ".HIM"), Position = new float[65, 65] };
        block.BoundingBox = new BoundingBox(new Vector3(x * 160, (64 - y) * 160, 0), new Vector3((x + 1) * 160, (65 - y) * 160, 1));
        terrain.Blocks[x, y] = block;
        return block;
    }
    [STAThread]
    static void Main(string[] args)
    {
        root = Path.Combine(Path.GetTempPath(), "rose-movement-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        Console.WriteLine("Test files: " + root);
        terrain = (Heightmaps)FormatterServices.GetUninitializedObject(typeof(Heightmaps));
        terrain.Blocks = new Heightmaps.Heightmap[100, 100];
        MapManager.Heightmaps = terrain;
        Add(31, 32); Add(32, 32); Add(31, 31);
        MovementMaps.Load(terrain);
        Check(MovementMaps.Error == null && MovementMaps.Blocks.Count == 3, "missing-grid load");
        Check(MovementMaps.Blocks.Values.All(b => b.Missing && b.File.IsWalkable.Cast<byte>().All(v => v == 0)), "no-MOV fallback");
        Check(MovementMaps.Save(false) == 0 && Directory.GetFiles(root, "*.MOV").Length == 0, "viewing must not write");
        int cx, cy;
        MovementMaps.Block sw = MovementMaps.Find(31 * 32, 32 * 32, out cx, out cy);
        Check(sw != null && sw.X == 31 && sw.Y == 32 && cx == 0 && cy == 0, "server south-west coordinates");
        MovementMaps.Block ne = MovementMaps.Find(31 * 32 + 31, 32 * 32 + 31, out cx, out cy);
        Check(ne == sw && cx == 31 && cy == 31, "server north-east coordinates");
        Check(MovementMaps.Find(-1, 1024, out cx, out cy) == null, "negative boundary");
        Check(MovementMaps.Find(2048, 1024, out cx, out cy) == null, "positive boundary");
        sw.File.IsWalkable[0, 0] = 1; sw.File.IsWalkable[31, 31] = 2; sw.Dirty = true;
        Check(MovementMaps.Save(false) == 3, "first edit must generate full coverage");
        string file = sw.File.FilePath;
        byte[] saved = File.ReadAllBytes(file);
        Check(saved.Length == 1032 && BitConverter.ToInt32(saved, 0) == 32 && BitConverter.ToInt32(saved, 4) == 32, "server header");
        Check(saved[8] == 1 && saved[1031] == 2 && saved[9] == 0, "server row ordering and raw values");
        MovementMaps.Load(terrain);
        Check(MovementMaps.Save(false) == 0, "reload is clean");
        sw = MovementMaps.Blocks[3132]; sw.File.IsWalkable[0, 0] = 0; sw.Dirty = true;
        Check(MovementMaps.Save(false) == 1, "only dirty existing files saved");
        string[] backups = Directory.GetFiles(Path.Combine(root, ".mov-backups"), "*.MOV", SearchOption.AllDirectories);
        Check(backups.Length == 1 && File.ReadAllBytes(backups[0]).SequenceEqual(saved), "original bytes backed up");
        sw.File.IsWalkable[0, 1] = 1; sw.Dirty = true;
        bool writeFailed = false;
        using (FileStream locked = File.Open(file, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            try { MovementMaps.Save(false); } catch (IOException) { writeFailed = true; }
        }
        Check(writeFailed && sw.Dirty && sw.File.FilePath == file, "failed save preserves dirty state and destination");
        Check(Directory.GetFiles(root, "*.tmp-*").Length == 0, "failed save cleans temporary file");
        Check(MovementMaps.Save(false) == 1, "failed save can be retried");
        File.Delete(MovementMaps.Blocks[3232].File.FilePath);
        MovementMaps.Load(terrain);
        Check(MovementMaps.Blocks[3232].File.IsWalkable.Cast<byte>().All(v => v == 1), "partial coverage fallback");
        Check(MovementMaps.Save(true) == 1, "generate only missing files");
        byte[] beforeMalformed = File.ReadAllBytes(file);
        File.WriteAllBytes(file, new byte[] { 32, 0 });
        MovementMaps.Load(terrain);
        Check(MovementMaps.Error != null && MovementMaps.Blocks.Count == 0, "malformed grid disables painting");
        bool rejected = false;
        try { MovementMaps.Save(true); } catch (InvalidOperationException) { rejected = true; }
        Check(rejected && File.ReadAllBytes(file).Length == 2, "malformed source never overwritten");
        File.WriteAllBytes(file, beforeMalformed);
        MovementMaps.Load(terrain);

        int realFiles = 0;
        foreach (string source in Directory.GetFiles(args[0], "*.MOV", SearchOption.AllDirectories))
        {
            if (source.Contains(".mov-backups")) continue;
            MOV mov = new MOV(source);
            string copy = Path.Combine(root, "roundtrip.mov"); mov.Save(copy);
            Check(File.ReadAllBytes(source).SequenceEqual(File.ReadAllBytes(copy)), "roundtrip " + source);
            realFiles++;
        }
        Console.WriteLine("PASS: codec, missing/partial coverage, server axes, backups, malformed-file protection; " + realFiles + " real MOV roundtrips.");
        RenderAndPaint();
    }

    static void RenderAndPaint()
    {
        using (System.Windows.Forms.Panel panel = new System.Windows.Forms.Panel())
        using (GraphicsDevice device = new GraphicsDevice(GraphicsAdapter.DefaultAdapter, DeviceType.Hardware, panel.Handle,
            new PresentationParameters { BackBufferWidth = 512, BackBufferHeight = 512, BackBufferFormat = SurfaceFormat.Color,
                BackBufferCount = 1, IsFullScreen = false, EnableAutoDepthStencil = true, AutoDepthStencilFormat = DepthFormat.Depth24,
                SwapEffect = SwapEffect.Discard, PresentationInterval = PresentInterval.Immediate }))
        using (Movement tool = new Movement(device))
        {
            Movement.Stroke stroke = new Movement.Stroke();
            FieldInfo strokeField = typeof(Movement).GetField("stroke", BindingFlags.Instance | BindingFlags.NonPublic);
            strokeField.SetValue(tool, stroke);
            tool.Value = 1; tool.Radius = 1;
            typeof(Movement).GetMethod("Paint", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(tool, new object[] { 31 * 32 + 31, 32 * 32 + 31 });
            Check(stroke.Changes.Count > 0 && stroke.Changes.Values.Select(c => c.Block).Distinct().Count() >= 2, "brush crosses block boundaries");
            stroke.Undo();
            Check(stroke.Changes.Values.All(c => c.Block.File.IsWalkable[c.Y, c.X] == c.Before), "stroke undo");
            stroke.Redo();
            Check(stroke.Changes.Values.All(c => c.Block.File.IsWalkable[c.Y, c.X] == c.After), "stroke redo");
            strokeField.SetValue(tool, null);

            MovementMaps.Block target = MovementMaps.Blocks[3132];
            for (int y = 0; y < 32; y++)
                for (int x = 0; x < 32; x++) target.File.IsWalkable[y, x] = (byte)(x < 16 ? 0 : 1);
            CameraManager.PerspectiveCamera = new Perspective();
            Vector3 center = new Vector3(31 * 160 + 80, 32 * 160 + 80, 0);
            typeof(Perspective).GetProperty("View").GetSetMethod(true).Invoke(CameraManager.PerspectiveCamera,
                new object[] { Matrix.CreateLookAt(center + new Vector3(0, 0, 250), center, Vector3.UnitY) });
            typeof(Perspective).GetProperty("Projection").GetSetMethod(true).Invoke(CameraManager.PerspectiveCamera,
                new object[] { Matrix.CreateOrthographic(180, 180, 1, 500) });
            using (RenderTarget2D render = new RenderTarget2D(device, 512, 512, 1, SurfaceFormat.Color))
            {
                device.SetRenderTarget(0, render);
                device.Clear(Color.Black);
                device.RenderState.AlphaBlendEnable = false;
                device.RenderState.DepthBufferWriteEnable = true;
                tool.Draw();
                Check(!device.RenderState.AlphaBlendEnable && device.RenderState.DepthBufferWriteEnable, "render state restoration");
                device.SetRenderTarget(0, null);
                Texture2D texture = render.GetTexture();
                Color[] pixels = new Color[512 * 512]; texture.GetData(pixels);
                Check(pixels.Count(c => c.G > c.R * 2) > 40000, "green allow overlay visible");
                Check(pixels.Count(c => c.R > c.G * 2) > 40000, "red block overlay visible");
                texture.Save(Path.Combine(root, "overlay.png"), ImageFileFormat.Png);
            }
            Console.WriteLine("PASS: cross-block brush, undo/redo, real XNA overlay drawing and render-state restoration.");
        }
    }
}
