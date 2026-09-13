using System;
using System.Windows;
using System.Windows.Controls;
using Map_Editor.Engine;
using Map_Editor.Engine.Terrain;
using Map_Editor.Engine.Tools;
using Map_Editor.Misc;

namespace Map_Editor.Forms.Controls
{
    public class MovementTool : UserControl
    {
        public MovementTool()
        {
            Movement tool = (Movement)ToolManager.Tool;
            StackPanel panel = new StackPanel { Margin = new Thickness(10) };
            Content = panel;
            panel.Children.Add(new TextBlock { Text = "Movement (.MOV)", FontSize = 18, Margin = new Thickness(0, 0, 0, 12) });
            if (MovementMaps.Error != null)
            {
                panel.Children.Add(new TextBlock { Text = MovementMaps.Error, TextWrapping = TextWrapping.Wrap });
                return;
            }
            RadioButton allow = new RadioButton { Content = "Green: allow monster movement", IsChecked = tool.Value == 0, Margin = new Thickness(0, 4, 0, 4) };
            RadioButton block = new RadioButton { Content = "Red: block monster movement", IsChecked = tool.Value != 0, Margin = new Thickness(0, 4, 0, 12) };
            allow.Checked += delegate { tool.FinishStroke(); tool.Value = 0; };
            block.Checked += delegate { tool.FinishStroke(); tool.Value = 1; };
            panel.Children.Add(allow);
            panel.Children.Add(block);
            panel.Children.Add(new TextBlock { Text = "Brush size (each cell is 5 x 5 meters)" });
            ComboBox size = new ComboBox { Margin = new Thickness(0, 5, 0, 12) };
            foreach (string label in new[] { "1 x 1 cell", "3 x 3 cells", "5 x 5 cells", "7 x 7 cells" }) size.Items.Add(label);
            size.SelectedIndex = tool.Radius;
            size.SelectionChanged += delegate { tool.FinishStroke(); tool.Radius = size.SelectedIndex; };
            panel.Children.Add(size);
            CheckBox overlay = new CheckBox { Content = "Show movement overlay", IsChecked = true };
            overlay.Checked += delegate { tool.ShowOverlay = true; };
            overlay.Unchecked += delegate { tool.ShowOverlay = false; };
            panel.Children.Add(overlay);
            panel.Children.Add(new TextBlock { Text = "Left-drag on the floor to paint. Yellow previews the brush. Use Undo / Redo for each stroke.\n\nBlue / purple cells have no MOV file yet (allowed / blocked). Saving generates missing files across the map.\n\nThese permissions affect monster wandering, fleeing and returning home. Players and monster chasing use other movement rules.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 12, 0, 12) });
            Button save = new Button { Content = "Save / generate MOV files", Padding = new Thickness(6) };
            TextBlock status = new TextBlock { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 10, 0, 0) };
            save.Click += delegate
            {
                try
                {
                    tool.FinishStroke();
                    int count = MovementMaps.Save(true);
                    status.Text = string.Format("Saved {0} MOV file(s). Restart the game server to apply. Previous files are in .mov-backups beside the map.", count);
                    Output.WriteLine(Output.MessageType.Event, status.Text);
                }
                catch (Exception ex)
                {
                    Output.WriteException("Movement files", ex);
                    status.Text = "Could not finish saving MOV files: " + ex.Message + "\nUnsaved changes remain available; retry after fixing the error.";
                }
            };
            panel.Children.Add(save);
            panel.Children.Add(status);
        }
    }
}
