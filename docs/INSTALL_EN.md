# Veri_Ufku — CPU core and optional environments

Linux desktop, CPython3.13.15, PySide6/QML. The chosen distribution route is Flatpak.
Install the CPU core with the reviewed lock (`uv sync --locked --no-dev`) for
source development; this is not a complete offline installer. Optional profiles:
formats, arrays, geospatial, audio, graphs, statistics-advanced, neural (CPU torch),
bayes, connectors, privacy and audio-speech. Select only the extras needed for a
compatible stack. Do not assume every model backend fits a single Python runtime.

The application does not automatically provision or route external worker
virtual environments. Incompatible stacks require a separately reviewed worker
contract and deployment; this capability is unavailable here. Environment profile
import is a data-only comparison, not pip execution or environment activation.

Open Report → package/environment status. Explicit refresh reads installed version
metadata, QML/plugin files, native distribution and driver presence; it does not
prove native/GPU execution. Artifact backend versions and local model folder bytes
can be inspected without loading executable model objects. No model is downloaded
on startup. Model weights/licenses/language are validated by their own adapters.

An application `.flatpak` bundle excludes its runtime, GPU drivers and operating
system prerequisites. A clean machine offline installer and local extras installer
are unavailable unless separately recorded as tested. A reused pinned runtime in a
fresh app sandbox is not a clean-machine offline installation test.

Updates are explicit host Flatpak operations. The GUI checks a locally selected
artifact digest and prepares a rollback plan; it does not install or restart the
application. A digest verifies integrity only: obtain it through an independently
trusted publisher channel. Unsigned local candidates are not authenticated releases.
Keep the previous application commit AND a separate complete backup of the closed
project. Reverting an application commit does not reverse project schema migration;
an older app may refuse a newer schema. Restore a backup into a separate directory
without overwriting later work.

Current systems tested, actual package proofs and untested limits are recorded in
[Phase74 evidence](evidence/PHASE74.md). Pardus/Debian and CachyOS/Arch are not
interchangeable certifications. No external release is published by the build/CI.
