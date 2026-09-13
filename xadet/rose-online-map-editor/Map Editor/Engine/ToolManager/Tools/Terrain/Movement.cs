using System;
using System.Collections.Generic;
using Map_Editor.Engine.Terrain;
using Map_Editor.Engine.Tools.Interfaces;
using Map_Editor.Engine.Commands.Interfaces;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;

namespace Map_Editor.Engine.Tools
{
    public class Movement : ITool, IDisposable
    {
        public byte Value;
        public int Radius;
        public bool ShowOverlay = true;
        private readonly GraphicsDevice device;
        private readonly BasicEffect effect;
        private readonly VertexDeclaration declaration;
        private Stroke stroke;
        private Point? hover, previous;
        private bool wasDown;
        private readonly VertexPositionColor[] vertices = new VertexPositionColor[32 * 32 * 24];

        private readonly VertexPositionColor[] lines = new VertexPositionColor[32 * 32 * 16];

        public class Change
        {
            public MovementMaps.Block Block;
            public int X, Y;
            public byte Before, After;
        }
        public class Stroke : ICommand
        {
            public readonly Dictionary<int, Change> Changes = new Dictionary<int, Change>();
            public void Undo() { Apply(false); }
            public void Redo() { Apply(true); }
            private void Apply(bool redo)
            {
                foreach (Change change in Changes.Values)
                {
                    change.Block.File.IsWalkable[change.Y, change.X] = redo ? change.After : change.Before;
                    change.Block.Dirty = true;
                }
            }
            public string GetName() { return "Movement painting"; }
        }

        public Movement(GraphicsDevice device)
        {
            this.device = device;
            effect = new BasicEffect(device, null) { VertexColorEnabled = true };
            declaration = new VertexDeclaration(device, VertexPositionColor.VertexElements);
        }

        public void FinishStroke()
        {
            if (stroke != null && stroke.Changes.Count != 0) UndoManager.AddCommand(stroke);
            stroke = null;
            previous = null;
        }

        public void Dispose() { FinishStroke(); effect.Dispose(); declaration.Dispose(); }

        private Vector3? Pick()
        {
            Ray ray = new Ray().Create(device, Mouse.GetState(), CameraManager.View, CameraManager.Projection);
            BoundingFrustum frustum = new BoundingFrustum(CameraManager.View * CameraManager.Projection);
            Vector3? closest = null;
            float distance = float.MaxValue;
            foreach (MovementMaps.Block block in MovementMaps.Blocks.Values)
                foreach (Vector3 point in block.Terrain.PickPosition(frustum, ray))
                {
                    float d = Vector3.DistanceSquared(ray.Position, point);
                    if (d < distance) { distance = d; closest = point; }
                }
            return closest;
        }

        public void Update(GameTime gameTime)
        {
            MouseState mouse = Mouse.GetState();
            bool down = mouse.LeftButton == ButtonState.Pressed;
            if (MapManager.Heightmaps.Loading || !App.Form.IsActive ||
                !mouse.Intersects(device.Viewport) || MovementMaps.Error != null ||
                mouse.RightButton == ButtonState.Pressed || mouse.MiddleButton == ButtonState.Pressed)
            {
                FinishStroke(); hover = null; wasDown = down; return;
            }
            Vector3? point = Pick();
            hover = point.HasValue ? (Point?)new Point((int)Math.Floor(point.Value.X / 5), (int)Math.Floor(point.Value.Y / 5)) : null;
            if (!down) FinishStroke();
            // Only start a stroke inside the viewport, never while returning from a UI click.
            if (down && !wasDown && hover.HasValue) stroke = new Stroke();
            if (stroke != null && hover.HasValue)
            {
                Point from = previous ?? hover.Value;
                Point to = hover.Value;
                int steps = Math.Max(Math.Abs(to.X - from.X), Math.Abs(to.Y - from.Y));
                for (int i = 0; i <= steps; i++)
                {
                    float t = steps == 0 ? 0 : (float)i / steps;
                    Paint((int)Math.Round(MathHelper.Lerp(from.X, to.X, t)), (int)Math.Round(MathHelper.Lerp(from.Y, to.Y, t)));
                }
                previous = to;
            }
            else previous = null;
            wasDown = down;
        }

        private void Paint(int gx, int gy)
        {
            for (int dy = -Radius; dy <= Radius; dy++)
                for (int dx = -Radius; dx <= Radius; dx++)
                {
                    int x, y;
                    MovementMaps.Block block = MovementMaps.Find(gx + dx, gy + dy, out x, out y);
                    if (block == null || block.File.IsWalkable[y, x] == Value) continue;
                    int key = (gx + dx) * 2048 + gy + dy;
                    Change change;
                    if (!stroke.Changes.TryGetValue(key, out change))
                    {
                        change = new Change { Block = block, X = x, Y = y, Before = block.File.IsWalkable[y, x] };
                        stroke.Changes.Add(key, change);
                    }
                    change.After = Value;
                    block.File.IsWalkable[y, x] = Value;
                    block.Dirty = true;
                }
        }

        private void AddLine(ref int count, Vector3 a, Vector3 b, Color color)
        {
            a.Z += .01f; b.Z += .01f;
            lines[count++] = new VertexPositionColor(a, color);
            lines[count++] = new VertexPositionColor(b, color);
        }

        public void Draw()
        {
            if (!ShowOverlay || MapManager.Heightmaps.Loading) return;
            BoundingFrustum frustum = new BoundingFrustum(CameraManager.View * CameraManager.Projection);
            // Effect state restoration does not cover our explicit RenderState assignments.
            VertexDeclaration oldDeclaration = device.VertexDeclaration;
            bool oldBlend = device.RenderState.AlphaBlendEnable;
            bool oldAlphaTest = device.RenderState.AlphaTestEnable;
            bool oldDepth = device.RenderState.DepthBufferEnable;
            bool oldDepthWrite = device.RenderState.DepthBufferWriteEnable;
            Blend oldSource = device.RenderState.SourceBlend, oldDestination = device.RenderState.DestinationBlend;
            BlendFunction oldFunction = device.RenderState.BlendFunction;
            CullMode oldCull = device.RenderState.CullMode;
            FillMode oldFill = device.RenderState.FillMode;
            effect.View = CameraManager.View;
            effect.Projection = CameraManager.Projection;
            effect.Begin(SaveStateMode.SaveState);
            try
            {
                device.VertexDeclaration = declaration;
                device.RenderState.CullMode = CullMode.None;
                device.RenderState.AlphaBlendEnable = true;
                device.RenderState.AlphaTestEnable = false;
                device.RenderState.BlendFunction = BlendFunction.Add;
                device.RenderState.FillMode = FillMode.Solid;
                device.RenderState.SourceBlend = Blend.SourceAlpha;
                device.RenderState.DestinationBlend = Blend.InverseSourceAlpha;
                device.RenderState.DepthBufferEnable = true;
                device.RenderState.DepthBufferWriteEnable = false;
                foreach (MovementMaps.Block block in MovementMaps.Blocks.Values)
                {
                    if (!frustum.OnScreen(block.Terrain.BoundingBox)) continue;
                    int count = 0, lineCount = 0;
                    float originX = block.X * 160f;
                    float originY = (64 - block.Y) * 160f;
                    effect.World = Matrix.CreateTranslation(originX, originY, 0);
                    for (int y = 0; y < 32; y++)
                        for (int x = 0; x < 32; x++)
                        {
                            byte value = block.File.IsWalkable[y, x];
                            Color color = value == 0 ? new Color(40, 210, 90, 85) : new Color(240, 75, 55, 110);
                            if (block.Missing) color = value == 0 ? new Color(70, 170, 210, 65) : new Color(175, 120, 200, 90);
                            int gx = block.X * 32 + x, gy = (64 - block.Y) * 32 + y;
                            if (hover.HasValue && Math.Abs(gx - hover.Value.X) <= Radius && Math.Abs(gy - hover.Value.Y) <= Radius)
                                color = new Color(255, 230, 80, 165);
                            // Four terrain quads per MOV cell, using the actual HIM triangle diagonal.
                            for (int sy = 0; sy < 2; sy++)
                                for (int sx = 0; sx < 2; sx++)
                                {
                                    int hx = x * 2 + sx, hy = 64 - y * 2 - sy;
                                    Vector3 a = new Vector3(hx * 2.5f, (64 - hy) * 2.5f, block.Terrain.HeightFile.Position[hy, hx] + .08f);
                                    Vector3 b = new Vector3((hx + 1) * 2.5f, a.Y, block.Terrain.HeightFile.Position[hy, hx + 1] + .08f);
                                    Vector3 c = new Vector3(a.X, a.Y + 2.5f, block.Terrain.HeightFile.Position[hy - 1, hx] + .08f);
                                    Vector3 d = new Vector3(b.X, c.Y, block.Terrain.HeightFile.Position[hy - 1, hx + 1] + .08f);
                                    vertices[count++] = new VertexPositionColor(a, color);
                                    vertices[count++] = new VertexPositionColor(b, color);
                                    vertices[count++] = new VertexPositionColor(c, color);
                                    vertices[count++] = new VertexPositionColor(b, color);
                                    vertices[count++] = new VertexPositionColor(d, color);
                                    vertices[count++] = new VertexPositionColor(c, color);
                                    Color edge = new Color(20, 35, 45, 160);
                                    if (sy == 0) AddLine(ref lineCount, a, b, edge);
                                    if (sy == 1) AddLine(ref lineCount, c, d, edge);
                                    if (sx == 0) AddLine(ref lineCount, a, c, edge);
                                    if (sx == 1) AddLine(ref lineCount, b, d, edge);
                                }
                        }
                    foreach (EffectPass pass in effect.CurrentTechnique.Passes)
                    {
                        pass.Begin();
                        device.DrawUserPrimitives(PrimitiveType.TriangleList, vertices, 0, count / 3);
                        device.DrawUserPrimitives(PrimitiveType.LineList, lines, 0, lineCount / 2);
                        pass.End();
                    }
                }
            }
            finally
            {
                effect.End();
                device.VertexDeclaration = oldDeclaration;
                device.RenderState.AlphaBlendEnable = oldBlend;
                device.RenderState.AlphaTestEnable = oldAlphaTest;
                device.RenderState.DepthBufferEnable = oldDepth;
                device.RenderState.DepthBufferWriteEnable = oldDepthWrite;
                device.RenderState.SourceBlend = oldSource;
                device.RenderState.DestinationBlend = oldDestination;
                device.RenderState.BlendFunction = oldFunction;
                device.RenderState.CullMode = oldCull;
                device.RenderState.FillMode = oldFill;
            }
        }
    }
}
