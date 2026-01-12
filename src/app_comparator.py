"""
Conflict Flagger AEC - Main Application

A modern desktop application for comparing IFC building models with BC3 budgets.
Features a macOS-style UI with drag & drop support and phase-based analysis.

ARCHITECTURE:
=============
This app uses a modular pipeline:
    IFC File ─┐
              ├─> Parsers ─> Matcher ─> Comparator ─> Reporter ─> Excel
    BC3 File ─┘

Each component is independent and configurable via PhaseConfig.
This allows different analysis depths without code duplication.

PHASES:
=======
- QUICK_CHECK: Fast validation (codes, units, quantities)
- FULL_ANALYSIS: Comprehensive comparison (all properties)

See src/phases/config.py for phase definitions.
"""

# CRITICAL: Early setup for frozen executables (PyInstaller on Windows/Wine)
import sys
import os

# Detect if this is a re-entry/child process spawned by the main app
# If the marker env var exists, this is a child - exit immediately
if os.environ.get('_CONFLICT_FLAGGER_CHILD_PROCESS'):
    sys.exit(0)

# Set marker for any child processes we might spawn
os.environ['_CONFLICT_FLAGGER_CHILD_PROCESS'] = '1'

import multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import os
import sys
import subprocess
from pathlib import Path

# Try to import PIL for logo display
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import tkinterdnd2 for drag & drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Handle imports for both development and standalone builds
try:
    # Development mode (running from source)
    from src.parsers.ifc_parser import IFCParser
    from src.parsers.bc3_parser import BC3Parser
    from src.matching.matcher import Matcher
    from src.comparison.comparator import Comparator
    from src.reporting.reporter import Reporter
    from src.phases.config import Phase, PHASES, get_phase_config
except ImportError:
    # Standalone mode (PyInstaller build)
    from parsers.ifc_parser import IFCParser
    from parsers.bc3_parser import BC3Parser
    from matching.matcher import Matcher
    from comparison.comparator import Comparator
    from reporting.reporter import Reporter
    from phases.config import Phase, PHASES, get_phase_config


class ModernUploadZone(tk.Canvas):
    """A modern upload zone widget with dashed/solid border states matching macOS design."""

    def __init__(self, parent, file_type, hint, on_click, on_drop=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.file_type = file_type  # ".IFC" or ".BC3"
        self.hint = hint
        self.on_click = on_click
        self.on_drop = on_drop  # Callback for when file is dropped
        self.is_uploaded = False
        self.filename = ""
        self.is_drag_over = False

        # Colors from design mockup
        self.bg_empty = "#FAFAFA"
        self.bg_uploaded = "#F0FFF4"
        self.bg_drag_over = "#E8F4FF"  # Light blue when dragging over
        self.border_empty = "#D2D2D7"
        self.border_uploaded = "#34C759"
        self.border_drag_over = "#0071E3"  # Blue when dragging over
        self.icon_bg_empty = "#E8E8ED"
        self.icon_bg_uploaded = "#D1FAE5"
        self.text_primary = "#1D1D1F"
        self.text_secondary = "#86868B"
        self.text_success = "#34C759"

        self.configure(
            width=250,
            height=160,
            bg=self.bg_empty,
            highlightthickness=0,
            cursor="hand2"
        )

        self.bind("<Button-1>", lambda e: self.on_click())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Register as drop target if tkinterdnd2 is available
        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<DropEnter>>', self._on_drag_enter)
            self.dnd_bind('<<DropLeave>>', self._on_drag_leave)
            self.dnd_bind('<<Drop>>', self._on_drop)

        self.draw()

    def _on_enter(self, event):
        if not self.is_uploaded and not self.is_drag_over:
            self.configure(bg="#F5F8FF")
            self.draw()

    def _on_leave(self, event):
        if not self.is_uploaded and not self.is_drag_over:
            self.configure(bg=self.bg_empty)
            self.draw()

    def _on_drag_enter(self, event):
        """Handle drag enter event."""
        self.is_drag_over = True
        self.configure(bg=self.bg_drag_over)
        self.draw()
        return event.action

    def _on_drag_leave(self, event):
        """Handle drag leave event."""
        self.is_drag_over = False
        if self.is_uploaded:
            self.configure(bg=self.bg_uploaded)
        else:
            self.configure(bg=self.bg_empty)
        self.draw()

    def _on_drop(self, event):
        """Handle file drop event."""
        self.is_drag_over = False

        # Parse the dropped file path(s)
        # tkinterdnd2 returns paths with curly braces if they contain spaces
        file_path = event.data.strip()
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]

        # Handle multiple files - just take the first one
        if ' ' in file_path and not os.path.exists(file_path):
            # Try to find the first valid file path
            parts = file_path.split()
            for part in parts:
                clean_part = part.strip('{}')
                if os.path.exists(clean_part):
                    file_path = clean_part
                    break

        # Check if file extension matches
        expected_ext = self.file_type.lower()  # ".ifc" or ".bc3"
        actual_ext = os.path.splitext(file_path)[1].lower()

        if actual_ext == expected_ext:
            # Valid file - call the drop callback
            if self.on_drop:
                self.on_drop(file_path)
        else:
            # Wrong file type - show error briefly
            self.configure(bg="#FFE5E5")  # Light red
            self.draw()
            self.after(500, lambda: self._reset_bg())

        return event.action

    def _reset_bg(self):
        """Reset background after invalid drop."""
        if self.is_uploaded:
            self.configure(bg=self.bg_uploaded)
        else:
            self.configure(bg=self.bg_empty)
        self.draw()

    def set_uploaded(self, filename):
        self.is_uploaded = True
        self.filename = filename
        self.configure(bg=self.bg_uploaded)
        self.draw()

    def reset(self):
        self.is_uploaded = False
        self.filename = ""
        self.configure(bg=self.bg_empty)
        self.draw()

    def draw(self):
        self.delete("all")

        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        # Draw rounded rectangle border
        if self.is_drag_over:
            border_color = self.border_drag_over
            dash_pattern = ()  # Solid when dragging
        elif self.is_uploaded:
            border_color = self.border_uploaded
            dash_pattern = ()
        else:
            border_color = self.border_empty
            dash_pattern = (8, 4)

        # Draw rounded rectangle
        radius = 12
        self._draw_rounded_rect(2, 2, w-2, h-2, radius, border_color, dash_pattern)

        # Draw icon background (circle)
        icon_size = 48
        icon_x = w // 2
        icon_y = 40
        icon_bg = self.icon_bg_uploaded if self.is_uploaded else self.icon_bg_empty

        self.create_oval(
            icon_x - icon_size//2, icon_y - icon_size//2,
            icon_x + icon_size//2, icon_y + icon_size//2,
            fill=icon_bg, outline=""
        )

        # Draw icon (checkmark if uploaded, building/document if not)
        icon_color = self.text_success if self.is_uploaded else self.text_secondary

        if self.is_uploaded:
            # Checkmark icon
            self.create_line(
                icon_x - 10, icon_y,
                icon_x - 3, icon_y + 8,
                icon_x + 12, icon_y - 8,
                fill=icon_color, width=2.5, capstyle=tk.ROUND, joinstyle=tk.ROUND
            )
        else:
            # Simple file/building icon
            if self.file_type == ".IFC":
                # Building icon - simplified
                self.create_rectangle(icon_x - 12, icon_y - 10, icon_x + 12, icon_y + 12,
                                     outline=icon_color, width=1.5)
                self.create_line(icon_x, icon_y - 14, icon_x, icon_y + 12,
                                fill=icon_color, width=1.5)
                self.create_line(icon_x - 12, icon_y, icon_x + 12, icon_y,
                                fill=icon_color, width=1.5)
            else:
                # Document icon
                self.create_rectangle(icon_x - 10, icon_y - 12, icon_x + 10, icon_y + 12,
                                     outline=icon_color, width=1.5)
                self.create_line(icon_x - 6, icon_y - 4, icon_x + 6, icon_y - 4,
                                fill=icon_color, width=1.5)
                self.create_line(icon_x - 6, icon_y + 2, icon_x + 6, icon_y + 2,
                                fill=icon_color, width=1.5)

        # File type label
        font_family = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"
        self.create_text(
            w // 2, 85,
            text=self.file_type,
            font=(font_family, 16, "bold"),
            fill=self.text_primary
        )

        # Hint text
        self.create_text(
            w // 2, 105,
            text=self.hint,
            font=(font_family, 11),
            fill=self.text_secondary
        )

        # Filename if uploaded
        if self.is_uploaded and self.filename:
            display_name = self.filename
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            self.create_text(
                w // 2, 130,
                text=display_name,
                font=(font_family, 11, "bold"),
                fill=self.text_success
            )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, color, dash):
        """Draw a rounded rectangle with optional dash pattern."""
        # Top line
        self.create_line(x1 + radius, y1, x2 - radius, y1, fill=color, width=2, dash=dash)
        # Right line
        self.create_line(x2, y1 + radius, x2, y2 - radius, fill=color, width=2, dash=dash)
        # Bottom line
        self.create_line(x2 - radius, y2, x1 + radius, y2, fill=color, width=2, dash=dash)
        # Left line
        self.create_line(x1, y2 - radius, x1, y1 + radius, fill=color, width=2, dash=dash)

        # Corners (arcs)
        self.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, start=90, extent=90,
                       style=tk.ARC, outline=color, width=2)
        self.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, start=0, extent=90,
                       style=tk.ARC, outline=color, width=2)
        self.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, start=270, extent=90,
                       style=tk.ARC, outline=color, width=2)
        self.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, start=180, extent=90,
                       style=tk.ARC, outline=color, width=2)


class ModernButton(tk.Canvas):
    """A modern button widget with disabled/active states matching macOS design."""

    def __init__(self, parent, text, on_click, **kwargs):
        super().__init__(parent, **kwargs)

        self.text = text
        self.on_click = on_click
        self.is_active = False
        self.is_hovered = False

        # Colors from design mockup
        self.bg_disabled = "#E8E8ED"
        self.bg_active = "#0071E3"
        self.bg_hover = "#0077ED"
        self.text_disabled = "#86868B"
        self.text_active = "#FFFFFF"

        self.configure(
            width=540,
            height=52,
            highlightthickness=0,
            cursor="hand2"
        )

        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self.draw()

    def _on_click(self, event):
        if self.is_active:
            self.on_click()

    def _on_enter(self, event):
        self.is_hovered = True
        self.draw()

    def _on_leave(self, event):
        self.is_hovered = False
        self.draw()

    def set_active(self, active):
        self.is_active = active
        self.configure(cursor="hand2" if active else "arrow")
        self.draw()

    def set_text(self, text):
        self.text = text
        self.draw()

    def draw(self):
        self.delete("all")

        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        # Background color
        if not self.is_active:
            bg_color = self.bg_disabled
            text_color = self.text_disabled
        elif self.is_hovered:
            bg_color = self.bg_hover
            text_color = self.text_active
        else:
            bg_color = self.bg_active
            text_color = self.text_active

        # Draw rounded rectangle
        radius = 10
        self._draw_rounded_rect_filled(0, 0, w, h, radius, bg_color)

        # Draw download icon
        icon_x = w // 2 - 85
        icon_y = h // 2

        # Arrow down
        self.create_line(icon_x, icon_y - 8, icon_x, icon_y + 4,
                        fill=text_color, width=2, capstyle=tk.ROUND)
        self.create_line(icon_x - 5, icon_y, icon_x, icon_y + 4,
                        fill=text_color, width=2, capstyle=tk.ROUND)
        self.create_line(icon_x + 5, icon_y, icon_x, icon_y + 4,
                        fill=text_color, width=2, capstyle=tk.ROUND)
        # Tray
        self.create_line(icon_x - 8, icon_y + 10, icon_x - 8, icon_y + 6,
                        fill=text_color, width=2, capstyle=tk.ROUND)
        self.create_line(icon_x - 8, icon_y + 10, icon_x + 8, icon_y + 10,
                        fill=text_color, width=2, capstyle=tk.ROUND)
        self.create_line(icon_x + 8, icon_y + 10, icon_x + 8, icon_y + 6,
                        fill=text_color, width=2, capstyle=tk.ROUND)

        # Text
        font_family = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"
        self.create_text(
            w // 2 + 10, h // 2,
            text=self.text,
            font=(font_family, 15, "bold"),
            fill=text_color
        )

    def _draw_rounded_rect_filled(self, x1, y1, x2, y2, radius, color):
        """Draw a filled rounded rectangle."""
        # Main rectangles
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=color, outline=color)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=color, outline=color)

        # Corner circles
        self.create_oval(x1, y1, x1 + 2*radius, y1 + 2*radius, fill=color, outline=color)
        self.create_oval(x2 - 2*radius, y1, x2, y1 + 2*radius, fill=color, outline=color)
        self.create_oval(x2 - 2*radius, y2 - 2*radius, x2, y2, fill=color, outline=color)
        self.create_oval(x1, y2 - 2*radius, x1 + 2*radius, y2, fill=color, outline=color)


class ConflictFlaggerApp:
    """
    Main application with modern macOS-style UI.

    Supports phase-based analysis:
    - Quick Check: Fast validation of codes, units, quantities
    - Full Analysis: Comprehensive property comparison
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Flagger")
        self.root.geometry("640x520")  # Slightly taller to accommodate phase selector
        self.root.resizable(False, False)

        # Colors from design mockup
        self.bg_color = "#F5F5F7"
        self.card_color = "#FFFFFF"
        self.titlebar_color = "#FAFAFA"
        self.border_color = "#E5E5E5"
        self.text_primary = "#1D1D1F"
        self.text_secondary = "#86868B"
        self.accent_green = "#34C759"
        self.accent_blue = "#0071E3"

        # File paths
        self.path_ifc = tk.StringVar()
        self.path_bc3 = tk.StringVar()

        # Phase selection (default to Full Analysis)
        self.selected_phase = tk.StringVar(value=Phase.FULL_ANALYSIS.value)

        # Configure root background
        self.root.configure(bg=self.bg_color)

        self._build_ui()

    def _build_ui(self):
        """Build the main user interface."""
        # Main container - use the full window, OS provides titlebar
        self.main_frame = tk.Frame(self.root, bg=self.card_color)
        self.main_frame.pack(fill="both", expand=True)

        # Content area (no custom titlebar - OS provides it)
        self._build_content()

    def _get_logo_path(self):
        """Get the path to the logo file, works in both dev and built app."""
        # Try development path first
        dev_path = Path(__file__).parent.parent / "app_design" / "Servitec logo.png"
        if dev_path.exists():
            return dev_path

        # Try relative to executable (for built app)
        if getattr(sys, 'frozen', False):
            # Running as compiled
            bundle_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            logo_path = bundle_dir / "app_design" / "Servitec logo.png"
            if logo_path.exists():
                return logo_path

        return None

    def _build_content(self):
        """Build the main content area with upload zones, phase selector, and button."""
        content = tk.Frame(self.main_frame, bg=self.card_color)
        content.pack(fill="both", expand=True, padx=40, pady=20)

        font_family = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"

        # Header with logo
        header_frame = tk.Frame(content, bg=self.card_color)
        header_frame.pack(fill="x", pady=(0, 20))

        title_label = tk.Label(
            header_frame,
            text="Genera Informe Excel",
            font=(font_family, 24, "bold"),
            bg=self.card_color,
            fg=self.text_primary
        )
        title_label.pack()

        self.subtitle_label = tk.Label(
            header_frame,
            text="Selecciona el model IFC i el pressupost BC3",
            font=(font_family, 14),
            bg=self.card_color,
            fg=self.text_secondary
        )
        self.subtitle_label.pack(pady=(8, 0))

        # Logo (top right corner, absolute position)
        if HAS_PIL:
            logo_path = self._get_logo_path()
            if logo_path:
                try:
                    # Load and resize logo (small)
                    logo_img = Image.open(logo_path)
                    logo_height = 25
                    aspect_ratio = logo_img.width / logo_img.height
                    logo_width = int(logo_height * aspect_ratio)
                    logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

                    # Keep reference to prevent garbage collection
                    self.logo_photo = ImageTk.PhotoImage(logo_img)

                    # Place logo in top-right of main content area
                    logo_label = tk.Label(
                        content,
                        image=self.logo_photo,
                        bg=self.card_color
                    )
                    logo_label.place(relx=1.0, y=0, anchor="ne")
                except Exception as e:
                    pass  # Silently fail if logo can't be loaded

        # Upload zones container
        zones_frame = tk.Frame(content, bg=self.card_color)
        zones_frame.pack(fill="x", pady=(0, 16))

        # IFC upload zone
        self.ifc_zone = ModernUploadZone(
            zones_frame,
            file_type=".IFC",
            hint="Model BIM",
            on_click=self.load_ifc,
            on_drop=self._on_ifc_drop,
            bg="#FAFAFA"
        )
        self.ifc_zone.pack(side="left", padx=(10, 10))

        # BC3 upload zone
        self.bc3_zone = ModernUploadZone(
            zones_frame,
            file_type=".BC3",
            hint="Pressupost",
            on_click=self.load_bc3,
            on_drop=self._on_bc3_drop,
            bg="#FAFAFA"
        )
        self.bc3_zone.pack(side="right", padx=(10, 10))

        # Phase selector
        self._build_phase_selector(content, font_family)

        # Arrow divider
        arrow_frame = tk.Frame(content, bg=self.card_color, height=30)
        arrow_frame.pack(fill="x", pady=(8, 16))

        arrow_canvas = tk.Canvas(arrow_frame, width=24, height=24, bg=self.card_color, highlightthickness=0)
        arrow_canvas.pack()

        # Draw arrow pointing down
        self.arrow_canvas = arrow_canvas
        self._draw_arrow()

        # Download button
        self.download_btn = ModernButton(
            content,
            text="Descarrega Excel",
            on_click=self.generate_excel_report,
            bg=self.card_color
        )
        self.download_btn.pack()

        # Status label
        self.status_label = tk.Label(
            content,
            text="",
            font=(font_family, 12),
            bg=self.card_color,
            fg=self.text_secondary
        )
        self.status_label.pack(pady=(15, 0))

    def _build_phase_selector(self, parent, font_family):
        """
        Build the phase selection UI.

        This allows users to choose between Quick Check and Full Analysis.
        The phase determines what comparisons are performed and how results
        are reported.
        """
        phase_frame = tk.Frame(parent, bg=self.card_color)
        phase_frame.pack(fill="x", pady=(0, 8))

        # Phase label
        phase_label = tk.Label(
            phase_frame,
            text="Tipus d'anàlisi:",
            font=(font_family, 12),
            bg=self.card_color,
            fg=self.text_secondary
        )
        phase_label.pack(side="left", padx=(10, 15))

        # Radio buttons for phase selection
        for phase in Phase:
            config = PHASES[phase]
            rb = tk.Radiobutton(
                phase_frame,
                text=config.name,
                variable=self.selected_phase,
                value=phase.value,
                font=(font_family, 12),
                bg=self.card_color,
                fg=self.text_primary,
                activebackground=self.card_color,
                selectcolor=self.card_color,
                cursor="hand2"
            )
            rb.pack(side="left", padx=(0, 20))

    def _draw_arrow(self, active=False):
        """Draw the arrow divider, green when both files are selected."""
        self.arrow_canvas.delete("all")
        color = self.accent_green if active else "#D2D2D7"

        # Arrow pointing down
        self.arrow_canvas.create_line(12, 3, 12, 18, fill=color, width=1.5, capstyle=tk.ROUND)
        self.arrow_canvas.create_line(5, 12, 12, 18, fill=color, width=1.5, capstyle=tk.ROUND)
        self.arrow_canvas.create_line(19, 12, 12, 18, fill=color, width=1.5, capstyle=tk.ROUND)

    def _update_button_state(self):
        """Update button state and subtitle based on file selection."""
        ifc_ready = bool(self.path_ifc.get())
        bc3_ready = bool(self.path_bc3.get())
        both_ready = ifc_ready and bc3_ready

        self.download_btn.set_active(both_ready)
        self._draw_arrow(both_ready)

        if both_ready:
            self.subtitle_label.config(text="Fitxers carregats - preparat per generar")
        elif ifc_ready:
            self.subtitle_label.config(text="IFC carregat - selecciona el fitxer BC3")
        elif bc3_ready:
            self.subtitle_label.config(text="BC3 carregat - selecciona el fitxer IFC")
        else:
            self.subtitle_label.config(text="Selecciona el model IFC i el pressupost BC3")

    def _set_status(self, msg):
        """Update the status label."""
        self.status_label.config(text=msg)
        self.root.update()

    def load_ifc(self):
        """Open file dialog to select IFC file."""
        f = filedialog.askopenfilename(
            title="Select IFC File",
            filetypes=[("IFC Files", "*.ifc"), ("All Files", "*.*")]
        )
        if f:
            self.path_ifc.set(f)
            filename = os.path.basename(f)
            self.ifc_zone.set_uploaded(filename)
            self._update_button_state()

    def load_bc3(self):
        """Open file dialog to select BC3 file."""
        f = filedialog.askopenfilename(
            title="Select BC3 File",
            filetypes=[("BC3 Files", "*.bc3"), ("All Files", "*.*")]
        )
        if f:
            self.path_bc3.set(f)
            filename = os.path.basename(f)
            self.bc3_zone.set_uploaded(filename)
            self._update_button_state()

    def _on_ifc_drop(self, file_path):
        """Handle IFC file drop."""
        self.path_ifc.set(file_path)
        filename = os.path.basename(file_path)
        self.ifc_zone.set_uploaded(filename)
        self._update_button_state()

    def _on_bc3_drop(self, file_path):
        """Handle BC3 file drop."""
        self.path_bc3.set(file_path)
        filename = os.path.basename(file_path)
        self.bc3_zone.set_uploaded(filename)
        self._update_button_state()

    # --- EXCEL GENERATION ---

    def _get_output_directory(self):
        """
        Determine the best output directory for the report.

        Priority:
        1. User's Downloads folder (default)
        2. User's Desktop (fallback)
        3. User's home directory (last resort)

        This ensures output is always in a user-accessible location,
        whether running in development or as a built .app/.exe.
        """
        # Default to Downloads folder
        downloads = Path.home() / "Downloads"
        if downloads.exists() and os.access(str(downloads), os.W_OK):
            return downloads

        # Fallback to Desktop
        desktop = Path.home() / "Desktop"
        if desktop.exists() and os.access(str(desktop), os.W_OK):
            return desktop

        # Ultimate fallback: home directory
        return Path.home()

    def _get_selected_phase(self) -> Phase:
        """Get the currently selected analysis phase."""
        phase_value = self.selected_phase.get()
        for phase in Phase:
            if phase.value == phase_value:
                return phase
        return Phase.FULL_ANALYSIS  # Default fallback

    def generate_excel_report(self):
        """
        Generate the Excel comparison report using the backend pipeline.

        The analysis depth depends on the selected phase:
        - QUICK_CHECK: Fast validation of codes, units, quantities
        - FULL_ANALYSIS: Comprehensive property comparison
        """
        if not self.path_ifc.get() or not self.path_bc3.get():
            messagebox.showwarning("Warning", "Please select both files.")
            return

        # Get selected phase and its configuration
        phase = self._get_selected_phase()
        phase_config = get_phase_config(phase)

        self._set_status(f"Starting {phase_config.name}...")
        self.download_btn.set_text("Processing...")
        self.download_btn.set_active(False)

        try:
            # Get a user-accessible output directory (works in both dev and built app)
            output_dir = self._get_output_directory()

            # 1. Parse IFC file using IFCParser
            self._set_status("Analyzing IFC file...")
            self.root.update()
            ifc_parser = IFCParser()
            ifc_result = ifc_parser.parse(self.path_ifc.get())
            self._set_status(f"IFC: {len(ifc_result.types)} types, {len(ifc_result.elements)} elements")
            self.root.update()

            # 2. Parse BC3 file using BC3Parser
            self._set_status("Analyzing BC3 file...")
            self.root.update()
            bc3_parser = BC3Parser()
            bc3_result = bc3_parser.parse(self.path_bc3.get())
            self._set_status(f"BC3: {len(bc3_result.elements)} items loaded")
            self.root.update()

            # 3. Match elements using Matcher
            self._set_status("Matching IFC elements with BC3 items...")
            self.root.update()
            matcher = Matcher(match_by_name=True)
            match_result = matcher.match(ifc_result, bc3_result)
            self._set_status(f"Matched: {len(match_result.matched)}")
            self.root.update()

            # 4. Compare matched elements using Comparator (configured by phase)
            self._set_status("Comparing elements...")
            self.root.update()
            comparator = Comparator(
                tolerance=phase_config.quantity_tolerance,
                compare_names=phase_config.check_names
            )
            comparison_result = comparator.compare(match_result, phase_config)
            summary = comparison_result.summary()
            self._set_status(f"Conflicts: {summary['total_conflicts']}")
            self.root.update()

            # 5. Generate report using Reporter (configured by phase)
            self._set_status("Generating Excel report...")
            self.root.update()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            phase_suffix = "quick" if phase == Phase.QUICK_CHECK else "full"
            output_path = output_dir / f"Report_AEC_{phase_suffix}_{timestamp}.xlsx"

            reporter = Reporter()
            report_path = reporter.generate_report(
                match_result,
                comparison_result,
                output_path,
                phase_config=phase_config
            )

            self._set_status(f"Report saved successfully")

            # Show success message with summary (in Catalan)
            messagebox.showinfo(
                "Informe Generat",
                f"L'informe s'ha generat correctament!\n\n"
                f"Tipus d'anàlisi: {phase_config.name}\n\n"
                f"Emparellats: {len(match_result.matched)} elements\n"
                f"Nomes a IFC (sense pressupostar): {len(match_result.ifc_only)}\n"
                f"Nomes a BC3 (sense modelar): {len(match_result.bc3_only)}\n\n"
                f"Discrepancies trobades: {summary['total_conflicts']}\n"
                f"  - Errors: {summary['errors']}\n"
                f"  - Avisos: {summary['warnings']}\n\n"
                f"Fitxer guardat a: {report_path}"
            )

            # Try to open the file (cross-platform)
            self._open_file_cross_platform(report_path)

        except FileNotFoundError as e:
            self._set_status(f"Error: File not found")
            messagebox.showerror("Error", f"File not found:\n{e}")
        except Exception as e:
            self._set_status(f"Error during analysis")
            messagebox.showerror("Error", f"Could not complete analysis:\n{e}")
        finally:
            # Restore button state
            self.download_btn.set_text("Descarrega Excel")
            self._update_button_state()

    def _open_file_cross_platform(self, file_path):
        """
        Open a file using the system's default application.

        This is a cross-platform solution that works on:
        - macOS: uses 'open' command
        - Windows: uses os.startfile
        - Linux: uses 'xdg-open' command
        """
        try:
            if sys.platform == "darwin":
                subprocess.run(['open', str(file_path)], check=False)
            elif sys.platform == "win32":
                os.startfile(str(file_path))
            else:
                subprocess.run(['xdg-open', str(file_path)], check=False)
        except Exception as open_error:
            self._set_status(f"Could not open file automatically")


def main():
    """Main entry point for the application."""
    # Use TkinterDnD if available for drag & drop support
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ConflictFlaggerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
