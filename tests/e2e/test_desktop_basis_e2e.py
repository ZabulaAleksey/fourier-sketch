"""Actual offscreen Qt freehand-to-selected-basis E2E for FS-032."""

import os
import time
from typing import ClassVar, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from fourier_sketch.application import TimelineState
from fourier_sketch.domain import BasisKind
from fourier_sketch.ui.desktop import DesktopWindow

pytestmark = pytest.mark.e2e


class _MemorySettings:
    values: ClassVar[dict[str, object]] = {}

    def __init__(self, *_args: object) -> None:
        pass

    def value(self, key: str, default: object, _type: object) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


def _mouse_event(
    event_type: QEvent.Type,
    point: QPointF,
    *,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        point,
        point,
        point,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


@pytest.mark.parametrize("basis", tuple(BasisKind))
def test_freehand_builds_and_animates_only_the_explicit_basis(
    basis: BasisKind,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _MemorySettings.values = {}
    monkeypatch.setattr("fourier_sketch.ui.desktop.QSettings", _MemorySettings)
    app = cast(QApplication, QApplication.instance() or QApplication([]))
    window = DesktopWindow()
    window.show()
    window._basis_selector.setCurrentIndex(
        window._basis_selector.findData(basis.value)
    )

    source = window._source
    source.mousePressEvent(
        _mouse_event(
            QEvent.Type.MouseButtonPress,
            QPointF(40.0, 80.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    for point in (QPointF(90.0, 35.0), QPointF(145.0, 115.0), QPointF(210.0, 60.0)):
        source.mouseMoveEvent(
            _mouse_event(
                QEvent.Type.MouseMove,
                point,
                button=Qt.MouseButton.NoButton,
                buttons=Qt.MouseButton.LeftButton,
            )
        )
    source.mouseReleaseEvent(
        _mouse_event(
            QEvent.Type.MouseButtonRelease,
            QPointF(260.0, 90.0),
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.NoButton,
        )
    )

    deadline = time.monotonic() + 5.0
    while window._job is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window._job is None
    assert window._selected_basis() is basis
    assert not window._basis_selector.isEnabled()

    if basis is BasisKind.FOURIER_EPICYCLE:
        assert window._timeline is not None
        assert window._haar_timeline is None
        assert window._canvas._frame is not None
        endpoint = window._canvas._frame.chain.endpoint
        window._timeline_action("play")
        window._timeline_action("advance", 0.1)
        assert window._canvas._frame is not None
        assert window._canvas._frame.chain.endpoint != endpoint
    elif basis is BasisKind.HAAR_WAVELET:
        assert window._timeline is None
        assert window._haar_timeline is not None
        assert window._indexed_timeline is None
        assert window._canvas._haar_frame is not None
        assert window._canvas._frame is None
        source_curve = window._canvas._haar_frame.source
        window._speed.setValue(window._speed.maximum())
        window._timeline_action("play")
        window._timeline_action("advance", 0.25)
        assert window._canvas._haar_frame is not None
        assert window._canvas._haar_frame.term_count == 2
        assert window._canvas._haar_frame.source is source_curve
        assert window._canvas._haar_frame.state is TimelineState.RUNNING
    else:
        assert window._timeline is None
        assert window._haar_timeline is None
        assert window._indexed_timeline is not None
        assert window._canvas._indexed_frame is not None
        assert window._canvas._frame is None
        assert window._canvas._haar_frame is None
        source_curve = window._canvas._indexed_frame.source
        window._speed.setValue(window._speed.maximum())
        window._timeline_action("play")
        window._timeline_action("advance", 0.25)
        assert window._canvas._indexed_frame is not None
        assert window._canvas._indexed_frame.term_count == 2
        assert window._canvas._indexed_frame.source is source_curve
        assert window._canvas._indexed_frame.state is TimelineState.RUNNING

    window.close()
