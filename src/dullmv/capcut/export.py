"""CapCut desktop export automation (Windows UI automation)."""

from __future__ import annotations

import shutil
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

if sys.platform != "win32":
    raise ImportError("CapCut export is only available on Windows")

import uiautomation as uia
from pycapcut import exceptions

CAPCUT_WINDOW_NAMES = ("CapCut", "剪映专业版")
EXPORT_WINDOW_NAMES = ("Export", "导出")


class ExportResolution(Enum):
    RES_8K = "8K"
    RES_4K = "4K"
    RES_2K = "2K"
    RES_1080P = "1080P"
    RES_720P = "720P"
    RES_480P = "480P"


class ExportFramerate(Enum):
    FR_24 = "24fps"
    FR_25 = "25fps"
    FR_30 = "30fps"
    FR_50 = "50fps"
    FR_60 = "60fps"


_RESOLUTION_MAP = {
    "8K": ExportResolution.RES_8K,
    "4K": ExportResolution.RES_4K,
    "2K": ExportResolution.RES_2K,
    "1080P": ExportResolution.RES_1080P,
    "720P": ExportResolution.RES_720P,
    "480P": ExportResolution.RES_480P,
}

_FRAMERATE_MAP = {
    24: ExportFramerate.FR_24,
    25: ExportFramerate.FR_25,
    30: ExportFramerate.FR_30,
    50: ExportFramerate.FR_50,
    60: ExportFramerate.FR_60,
}


class AutomationError(RuntimeError):
    """Raised when CapCut UI automation fails."""


class ControlFinder:
    @staticmethod
    def desc_matcher(
        target_desc: str, depth: int = 2, exact: bool = False
    ) -> Callable[[uia.Control, int], bool]:
        target_desc = target_desc.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            full_desc: str = control.GetPropertyValue(30159).lower()
            return (target_desc == full_desc) if exact else (target_desc in full_desc)

        return matcher

    @staticmethod
    def class_name_matcher(
        class_name: str, depth: int = 1, exact: bool = False
    ) -> Callable[[uia.Control, int], bool]:
        class_name = class_name.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            current = control.ClassName.lower()
            return (class_name == current) if exact else (class_name in current)

        return matcher


class CapCutController:
    """Automate CapCut desktop export via UI automation."""

    app: uia.WindowControl
    app_status: Literal["home", "edit", "pre_export"]

    def __init__(self) -> None:
        self.get_window()

    def export_draft(
        self,
        draft_name: str,
        output_path: Path | str | None = None,
        *,
        resolution: ExportResolution | None = None,
        framerate: ExportFramerate | None = None,
        timeout: float = 1200,
    ) -> None:
        output = Path(output_path).resolve() if output_path is not None else None
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting CapCut draft '{draft_name}'...")
        self.get_window()
        self.switch_to_home()

        draft_title = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(f"HomePageDraftTitle:{draft_name}", exact=True),
        )
        if not draft_title.Exists(0):
            raise exceptions.DraftNotFound(f"Draft not found in CapCut home: {draft_name}")

        draft_btn = draft_title.GetParentControl()
        if draft_btn is None:
            raise AutomationError(f"Could not open draft control for: {draft_name}")
        draft_btn.Click(simulateMove=False)
        time.sleep(10)
        self.get_window()

        export_btn = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn"),
        )
        if not export_btn.Exists(0):
            raise AutomationError("Export button not found in editor window")
        export_btn.Click(simulateMove=False)
        time.sleep(10)
        self.get_window()

        export_path_sib = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("ExportPath"),
        )
        if not export_path_sib.Exists(0):
            raise AutomationError("Export path control not found")
        export_path_text = export_path_sib.GetSiblingControl(lambda _ctrl: True)
        if export_path_text is None:
            raise AutomationError("Export path text control not found")
        export_path = export_path_text.GetPropertyValue(30159)

        if resolution is not None:
            self._set_export_dropdown("ExportSharpnessInput", resolution.value)
        if framerate is not None:
            self._set_export_dropdown("FrameRateInput", framerate.value)

        ok_btn = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True),
        )
        if not ok_btn.Exists(0):
            raise AutomationError("Final export button not found")
        ok_btn.Click(simulateMove=False)
        time.sleep(5)

        started = time.time()
        while True:
            self.get_window()
            if self.app_status != "pre_export":
                time.sleep(1)
                continue

            close_btn = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportSucceedCloseBtn"),
            )
            if close_btn.Exists(0):
                close_btn.Click(simulateMove=False)
                break

            if time.time() - started > timeout:
                raise AutomationError(f"Export timed out after {int(timeout)} seconds")

            time.sleep(1)

        time.sleep(2)
        self.get_window()
        self.switch_to_home()
        time.sleep(2)

        if output is not None:
            source = Path(str(export_path))
            if not source.is_file():
                raise AutomationError(f"Exported file missing: {source}")
            if output.exists():
                output.unlink()
            shutil.move(str(source), str(output))
            print(f"Saved: {output}")

    def _set_export_dropdown(self, control_desc: str, item_value: str) -> None:
        setting_group = self.app.GroupControl(
            searchDepth=1,
            Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"),
        )
        if not setting_group.Exists(0):
            raise AutomationError("Export settings panel not found")

        dropdown = setting_group.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(control_desc),
        )
        if not dropdown.Exists(0.5):
            raise AutomationError(f"Export control not found: {control_desc}")
        dropdown.Click(simulateMove=False)
        time.sleep(0.5)

        item = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(item_value),
        )
        if not item.Exists(0.5):
            raise AutomationError(f"Export option not found: {item_value}")
        item.Click(simulateMove=False)
        time.sleep(0.5)

    def switch_to_home(self) -> None:
        if self.app_status == "home":
            return
        if self.app_status != "edit":
            raise AutomationError("Can only switch to home from edit mode")
        close_btn = self.app.GroupControl(searchDepth=1, ClassName="TitleBarButton", foundIndex=3)
        close_btn.Click(simulateMove=False)
        time.sleep(2)
        self.get_window()

    def get_window(self) -> None:
        if hasattr(self, "app") and self.app.Exists(0):
            self.app.SetTopmost(False)

        self.app = uia.WindowControl(searchDepth=1, Compare=self._window_matcher)
        if not self.app.Exists(0):
            raise AutomationError(
                "CapCut window not found. Open CapCut on the drafts home screen first."
            )

        for export_name in EXPORT_WINDOW_NAMES:
            export_window = self.app.WindowControl(searchDepth=1, Name=export_name)
            if export_window.Exists(0):
                self.app = export_window
                self.app_status = "pre_export"
                break

        self.app.SetActive()
        self.app.SetTopmost()

    def _window_matcher(self, control: uia.WindowControl, _depth: int) -> bool:
        if control.Name not in CAPCUT_WINDOW_NAMES:
            return False
        class_name = control.ClassName.lower()
        if "homepage" in class_name:
            self.app_status = "home"
            return True
        if "mainwindow" in class_name:
            self.app_status = "edit"
            return True
        return False


def resolve_resolution(name: str | None) -> ExportResolution | None:
    if name is None:
        return None
    return _RESOLUTION_MAP.get(name)


def resolve_framerate(value: int | None) -> ExportFramerate | None:
    if value is None:
        return None
    return _FRAMERATE_MAP.get(value)
