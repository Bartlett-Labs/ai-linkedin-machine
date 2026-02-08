#!/usr/bin/env python3
"""
Image Optimizer GUI - Simple drag-and-drop interface for image resizing.

Features:
- Drag & drop image loading
- Platform/preset selection via dropdown
- Live preview of resized image
- One-click export

Usage:
    python -m image_optimizer.gui
    # or
    python image_optimizer/gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import io

try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .optimizer import ImageOptimizer, OutputFormat
from .strategies import ResizeStrategy
from .presets import SIZE_PRESETS


class ImageOptimizerGUI:
    """Main GUI application for the image optimizer."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Optimizer")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)

        # Initialize state
        self.source_image: Optional[Image.Image] = None
        self.source_path: Optional[Path] = None
        self.preview_image: Optional[ImageTk.PhotoImage] = None
        self.optimizer = ImageOptimizer()

        # Build UI
        self._create_widgets()
        self._setup_drag_drop()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Drop Zone / Preview Area ===
        self.preview_frame = ttk.LabelFrame(main_frame, text="Drop Image Here", padding="10")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Preview canvas
        self.canvas = tk.Canvas(
            self.preview_frame,
            bg="#f0f0f0",
            highlightthickness=2,
            highlightbackground="#cccccc"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Placeholder text
        self.placeholder_id = self.canvas.create_text(
            0, 0,
            text="Drag & Drop an image here\nor click to browse",
            font=("Arial", 14),
            fill="#888888",
            anchor="center"
        )

        # Bind click to browse
        self.canvas.bind("<Button-1>", lambda e: self._browse_image())
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # === Image Info ===
        self.info_label = ttk.Label(main_frame, text="No image loaded", font=("Arial", 10))
        self.info_label.pack(pady=(0, 10))

        # === Controls Frame ===
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Platform selector
        ttk.Label(controls_frame, text="Platform:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.platform_var = tk.StringVar(value="linkedin")
        self.platform_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.platform_var,
            values=list(SIZE_PRESETS.keys()),
            state="readonly",
            width=15
        )
        self.platform_combo.grid(row=0, column=1, padx=(0, 15))
        self.platform_combo.bind("<<ComboboxSelected>>", self._on_platform_change)

        # Preset selector
        ttk.Label(controls_frame, text="Size:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.preset_var,
            state="readonly",
            width=25
        )
        self.preset_combo.grid(row=0, column=3, padx=(0, 15))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        # Strategy selector
        ttk.Label(controls_frame, text="Strategy:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.strategy_var = tk.StringVar(value="crop_center")
        self.strategy_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.strategy_var,
            values=[s.value for s in ResizeStrategy if s != ResizeStrategy.CROP_SMART],
            state="readonly",
            width=12
        )
        self.strategy_combo.grid(row=0, column=5)
        self.strategy_combo.bind("<<ComboboxSelected>>", self._update_preview)

        # Initialize preset list
        self._update_preset_list()

        # === Custom Size Frame ===
        custom_frame = ttk.Frame(main_frame)
        custom_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(custom_frame, text="Or custom size:").pack(side=tk.LEFT, padx=(0, 10))

        self.width_var = tk.StringVar()
        self.width_entry = ttk.Entry(custom_frame, textvariable=self.width_var, width=6)
        self.width_entry.pack(side=tk.LEFT)

        ttk.Label(custom_frame, text=" x ").pack(side=tk.LEFT)

        self.height_var = tk.StringVar()
        self.height_entry = ttk.Entry(custom_frame, textvariable=self.height_var, width=6)
        self.height_entry.pack(side=tk.LEFT)

        ttk.Label(custom_frame, text=" px").pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(custom_frame, text="Apply Custom", command=self._apply_custom_size).pack(side=tk.LEFT)

        # === Output Size Display ===
        self.size_label = ttk.Label(main_frame, text="Output: --", font=("Arial", 11, "bold"))
        self.size_label.pack(pady=(0, 10))

        # === Action Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="Browse Image...",
            command=self._browse_image
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="Export as PNG",
            command=lambda: self._export_image(OutputFormat.PNG)
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Export as JPEG",
            command=lambda: self._export_image(OutputFormat.JPEG)
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Export as WebP",
            command=lambda: self._export_image(OutputFormat.WEBP)
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Batch export button
        ttk.Button(
            button_frame,
            text="Export All Sizes...",
            command=self._export_all_sizes
        ).pack(side=tk.RIGHT)

    def _setup_drag_drop(self):
        """Setup drag and drop functionality."""
        # Try to use tkinterdnd2 if available, otherwise use basic file dialog
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            # If we have tkinterdnd2, enhance the root window
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self._on_drop)
        except ImportError:
            # Fallback: just use click to browse
            pass

    def _on_drop(self, event):
        """Handle file drop event."""
        file_path = event.data
        # Clean up path (remove braces on Windows)
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        self._load_image(file_path)

    def _browse_image(self):
        """Open file dialog to browse for image."""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tiff"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self._load_image(file_path)

    def _load_image(self, file_path: str):
        """Load an image from file."""
        try:
            path = Path(file_path)
            self.source_image = Image.open(path)
            self.source_image.load()  # Force load into memory
            self.source_path = path

            # Update info label
            w, h = self.source_image.size
            size_kb = path.stat().st_size / 1024
            self.info_label.config(
                text=f"Loaded: {path.name} | {w} x {h} px | {size_kb:.1f} KB"
            )

            # Update preview frame title
            self.preview_frame.config(text=f"Preview: {path.name}")

            # Update preview
            self._update_preview()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{e}")

    def _on_canvas_resize(self, event):
        """Handle canvas resize to reposition placeholder."""
        # Move placeholder to center
        self.canvas.coords(self.placeholder_id, event.width // 2, event.height // 2)
        # Update preview if image loaded
        if self.source_image:
            self._update_preview()

    def _update_preset_list(self):
        """Update preset dropdown based on selected platform."""
        platform = self.platform_var.get()
        presets = SIZE_PRESETS.get(platform, {})

        # Format preset names with dimensions
        preset_items = []
        for name, (w, h) in sorted(presets.items()):
            preset_items.append(f"{name} ({w}x{h})")

        self.preset_combo['values'] = preset_items
        if preset_items:
            self.preset_combo.current(0)
            self._on_preset_change()

    def _on_platform_change(self, event=None):
        """Handle platform selection change."""
        self._update_preset_list()

    def _on_preset_change(self, event=None):
        """Handle preset selection change."""
        self._update_size_display()
        self._update_preview()

    def _get_current_size(self) -> tuple:
        """Get the currently selected target size."""
        platform = self.platform_var.get()
        preset_str = self.preset_var.get()

        if not preset_str:
            return (100, 100)

        # Extract preset name from combo box value
        preset_name = preset_str.split(" (")[0]
        presets = SIZE_PRESETS.get(platform, {})
        return presets.get(preset_name, (100, 100))

    def _update_size_display(self):
        """Update the output size display."""
        w, h = self._get_current_size()
        self.size_label.config(text=f"Output: {w} x {h} px")

    def _apply_custom_size(self):
        """Apply custom size from entry fields."""
        try:
            w = int(self.width_var.get())
            h = int(self.height_var.get())
            if w <= 0 or h <= 0:
                raise ValueError("Size must be positive")

            self.size_label.config(text=f"Output: {w} x {h} px (custom)")
            self._update_preview(custom_size=(w, h))
        except ValueError as e:
            messagebox.showwarning("Invalid Size", f"Please enter valid dimensions.\n{e}")

    def _update_preview(self, event=None, custom_size=None):
        """Update the preview image."""
        if not self.source_image:
            return

        # Get target size
        if custom_size:
            target_w, target_h = custom_size
        else:
            target_w, target_h = self._get_current_size()

        # Get strategy
        strategy = ResizeStrategy(self.strategy_var.get())

        # Resize the image
        resized = self.optimizer.resize(
            self.source_image.copy(),
            target_w,
            target_h,
            strategy
        )

        # Calculate preview size to fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # Scale preview to fit canvas while maintaining aspect
        img_w, img_h = resized.size
        scale = min(canvas_w / img_w, canvas_h / img_h, 1.0) * 0.9  # 90% of available space

        preview_w = int(img_w * scale)
        preview_h = int(img_h * scale)

        # Create preview image
        preview = resized.resize((preview_w, preview_h), Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        self.preview_image = ImageTk.PhotoImage(preview)

        # Clear canvas and draw preview
        self.canvas.delete("all")
        x = canvas_w // 2
        y = canvas_h // 2
        self.canvas.create_image(x, y, image=self.preview_image, anchor="center")

        # Draw border around preview
        x1 = x - preview_w // 2
        y1 = y - preview_h // 2
        x2 = x + preview_w // 2
        y2 = y + preview_h // 2
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#007acc", width=2)

        # Draw actual size label
        self.canvas.create_text(
            x, y2 + 15,
            text=f"Actual size: {target_w} x {target_h}",
            font=("Arial", 9),
            fill="#666666"
        )

    def _export_image(self, fmt: OutputFormat):
        """Export the resized image."""
        if not self.source_image:
            messagebox.showwarning("No Image", "Please load an image first.")
            return

        # Get target size
        target_w, target_h = self._get_current_size()

        # Try custom size if entered
        if self.width_var.get() and self.height_var.get():
            try:
                target_w = int(self.width_var.get())
                target_h = int(self.height_var.get())
            except ValueError:
                pass

        # Get strategy
        strategy = ResizeStrategy(self.strategy_var.get())

        # Ask for save location
        default_name = f"{self.source_path.stem}_{target_w}x{target_h}.{fmt.value}"
        file_path = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=f".{fmt.value}",
            initialfile=default_name,
            filetypes=[
                (f"{fmt.value.upper()} files", f"*.{fmt.value}"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        # Perform optimization
        result = self.optimizer.optimize_image(
            image_path=self.source_path,
            target_width=target_w,
            target_height=target_h,
            output_path=file_path,
            strategy=strategy,
            output_format=fmt,
        )

        if result.success:
            size_kb = result.new_file_size / 1024
            messagebox.showinfo(
                "Export Successful",
                f"Image saved to:\n{result.output_path}\n\n"
                f"Size: {result.new_size[0]} x {result.new_size[1]}\n"
                f"File size: {size_kb:.1f} KB"
            )
        else:
            messagebox.showerror("Export Failed", result.message)

    def _export_all_sizes(self):
        """Export all sizes for the selected platform."""
        if not self.source_image:
            messagebox.showwarning("No Image", "Please load an image first.")
            return

        platform = self.platform_var.get()

        # Ask for output directory
        output_dir = filedialog.askdirectory(
            title=f"Select Output Directory for {platform.title()} Icons"
        )

        if not output_dir:
            return

        # Get all presets for platform
        presets = [(platform, name) for name in SIZE_PRESETS[platform].keys()]
        strategy = ResizeStrategy(self.strategy_var.get())

        # Perform batch optimization
        results = self.optimizer.batch_optimize(
            image_path=self.source_path,
            presets=presets,
            output_dir=output_dir,
            strategy=strategy,
            output_format=OutputFormat.PNG,
        )

        success_count = sum(1 for r in results if r.success)

        if success_count == len(results):
            messagebox.showinfo(
                "Batch Export Successful",
                f"Exported {success_count} images to:\n{output_dir}"
            )
        else:
            failed = [r.message for r in results if not r.success]
            messagebox.showwarning(
                "Batch Export Completed",
                f"Exported {success_count}/{len(results)} images.\n\n"
                f"Failures:\n" + "\n".join(failed[:5])
            )


def main():
    """Launch the GUI application."""
    if not PILLOW_AVAILABLE:
        print("Error: Pillow is required. Install with: pip install Pillow")
        return 1

    # Try to use TkinterDnD for drag-drop support
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        # Fallback to standard Tk
        root = tk.Tk()

    app = ImageOptimizerGUI(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    main()
