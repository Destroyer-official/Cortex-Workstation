"""License & Tiers page: current entitlement, offline activation, trial.

Why a dedicated page: licensing used to be invisible inside the premium shell -
a user could hit a gated action and only learn about tiers from a denial
dialog. This page makes the entitlement state legible (tier, status, masked
key, unlocked-feature count), gives the activation / trial / deactivation
flows a home, and shows the full tier matrix from
:data:`cortex_unified.licensing.tiers.FEATURE_MIN_TIER` so "what do I get if I
upgrade" is answerable without reading the source.

All state flows through :meth:`LicensePage._refresh`, called once in the
constructor and after every action, so the page is always a plain projection of
:meth:`LicenseManager.validate` - no second source of truth to drift.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from cortex_unified.licensing import Tier
from cortex_unified.licensing.license_manager import (
    LicenseState,
    get_license_manager,
)
from cortex_unified.licensing.tiers import FEATURE_MIN_TIER

from .widgets import Card, title_block
from .window import _Page

_LOG = logging.getLogger("cortex.ui.premium")


class LicensePage(_Page):
    """Licensepage.

    Manages LicensePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "License & Tiers",
            "Activate a key, start the free PRO trial, or compare what each "
            "tier unlocks.",
        ))

        # -- current entitlement card -------------------------------------
        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(8)
        self.tier_label = QLabel("Free")
        self.tier_label.setObjectName("Metric")
        cl.addWidget(self.tier_label)
        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        cl.addWidget(self.status_label)
        self.key_label = QLabel("")
        self.key_label.setObjectName("Muted")
        cl.addWidget(self.key_label)
        self.features_label = QLabel("")
        cl.addWidget(self.features_label)
        self.v.addWidget(card)

        # -- activation / lifecycle card ----------------------------------
        act = Card(self.p)
        al = QVBoxLayout(act)
        al.setContentsMargins(22, 20, 22, 20)
        al.setSpacing(10)
        heading = QLabel("Manage License")
        heading.setObjectName("SectionTitle")
        al.addWidget(heading)

        form = QFormLayout()
        form.setSpacing(8)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Paste your license key")
        form.addRow("License key", self.key_edit)
        # Purchased tier travels with the key; data() carries the Tier enum so
        # nothing ever has to parse display text back.
        self.tier_combo = QComboBox()
        for tier in (Tier.PREMIUM, Tier.PRO, Tier.SUPER, Tier.ENTERPRISE):
            self.tier_combo.addItem(tier.value.title(), tier)
        form.addRow("Tier", self.tier_combo)
        self.name_edit = QLineEdit()
        form.addRow("Name", self.name_edit)
        self.email_edit = QLineEdit()
        form.addRow("Email", self.email_edit)
        al.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setObjectName("Primary")
        self.activate_btn.clicked.connect(self._activate)
        actions.addWidget(self.activate_btn)
        # Visible/enabled only while the one-per-machine PRO trial is still
        # available (mirrors start_trial's preconditions - see _refresh).
        self.trial_btn = QPushButton("Start Free Trial")
        self.trial_btn.clicked.connect(self._start_trial)
        actions.addWidget(self.trial_btn)
        self.deactivate_btn = QPushButton("Deactivate")
        self.deactivate_btn.clicked.connect(self._deactivate)
        actions.addWidget(self.deactivate_btn)
        al.addLayout(actions)
        self.v.addWidget(act)

        # -- tier comparison card -----------------------------------------
        comp = Card(self.p)
        tl = QVBoxLayout(comp)
        tl.setContentsMargins(22, 20, 22, 20)
        tl.setSpacing(10)
        comp_title = QLabel("What each tier unlocks")
        comp_title.setObjectName("SectionTitle")
        tl.addWidget(comp_title)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Feature", "Minimum tier", "Included"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(280)
        tl.addWidget(self.table)
        self.v.addWidget(comp)

        self.v.addStretch(1)
        self._refresh()

    # -- state ------------------------------------------------------------

    def _refresh(self) -> None:
        """Project the live license state onto every control.

        Validation is memoised by the manager (keyed to the license file), so
        calling this after every action is effectively free.
        """
        try:
            state = get_license_manager().validate()
        except Exception as exc:  # noqa: BLE001 - fail closed to Free, never crash
            _LOG.debug("could not validate license for display: %s", exc)
            state = LicenseState()

        self.tier_label.setText(state.tier.value.title())
        if state.licensed and state.trial:
            line = f"Trial \u2014 expires {state.expiry}"
        elif state.licensed:
            line = f"Licensed \u2014 expires {state.expiry}"
        else:
            line = f"Free \u2014 {state.reason}"
        if state.grace_active:
            line += " (grace period active)"
        self.status_label.setText(line)

        masked = state.to_dict()["key"]
        self.key_label.setText(f"Key: {masked}" if masked else "No key installed")
        self.features_label.setText(
            f"{len(state.features)} of {len(FEATURE_MIN_TIER)} features unlocked")

        trial_available = not state.licensed and not state.trial
        self.trial_btn.setVisible(trial_available)
        self.trial_btn.setEnabled(trial_available)
        self.deactivate_btn.setEnabled(state.licensed or bool(masked))

        self._fill_table(state)

    def _fill_table(self, state) -> None:
        """One row per feature, grouped by minimum tier then name.

        The 'Included' column is plain text ('Yes' or an em-dash) rather than
        check glyphs: Qt 6 ships no fonts, so codepoints rendered as colour
        emoji or tofu boxes depending on the machine.
        """
        rows = sorted(FEATURE_MIN_TIER.items(),
                      key=lambda kv: (kv[1].rank, kv[0].value))
        self.table.setRowCount(len(rows))
        for r, (feature, minimum) in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(feature.value))
            self.table.setItem(r, 1, QTableWidgetItem(minimum.value.title()))
            included = "Yes" if state.allows(feature) else "\u2014"
            self.table.setItem(r, 2, QTableWidgetItem(included))

    # -- actions ----------------------------------------------------------

    def _activate(self) -> None:
        """Activate.

        Manages activate operations and coordinates related state changes for the component.
        """
        try:
            state = get_license_manager().activate(
                self.key_edit.text(),
                self.tier_combo.currentData(),
                self.name_edit.text(),
                self.email_edit.text(),
            )
        except ValueError as exc:
            _LOG.info("activation rejected: %s", exc)
            QMessageBox.warning(self, "Activation failed", str(exc))
            return
        except RuntimeError as exc:  # defensive: manager raises ValueError today
            QMessageBox.warning(self, "Activation failed", str(exc))
            return
        _LOG.info("activated from GUI: tier=%s", state.tier.value)
        self.win.statusBar().showMessage(
            f"Activated \u2014 {state.tier.value.title()} edition.", 6000)
        self._refresh()

    def _start_trial(self) -> None:
        """Start the once-per-machine PRO trial.

        Manages start trial operations and coordinates related state changes for the component.
        """
        try:
            state = get_license_manager().start_trial()
        except RuntimeError as exc:
            # Already trialed / licensed between render and click - inform.
            _LOG.info("trial refused from License page: %s", exc)
            QMessageBox.information(self, "Trial unavailable", str(exc))
            self._refresh()
            return
        _LOG.info("PRO trial started from GUI (expires %s)", state.expiry)
        self.win.statusBar().showMessage(
            f"Free PRO trial started \u2014 expires {state.expiry}.", 6000)
        self._refresh()

    def _deactivate(self) -> None:
        """Deactivate.

        Manages deactivate operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Deactivate license",
            "Remove the license from this machine?\n\n"
            "The app returns to the Free tier immediately.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        get_license_manager().deactivate()
        _LOG.info("license deactivated from GUI")
        self.win.statusBar().showMessage("License deactivated.", 6000)
        self._refresh()
