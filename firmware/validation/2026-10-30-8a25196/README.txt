A-14329-MB00 r10 independent offline inspection - 2026-10-30

manifest.json and SHA256SUMS identify the exact downloaded credential-free build
41067820915, source 8a2519687a32ab4e683d93b74662811606761bbf.
image-inspection.json checks its actual kernel/uImage/fwtool CRCs, metadata and
appended DTB. rootfs-inspection.json checks the actual SquashFS inventory, selected
packages/modules/autoload/services/defaults and all 13 custom files against that
exact source. summary.json links the build/check workflows and current handoff.
The 170 packages and 79 modules are inventories, not proof of runtime behavior.

The full binaries and expanded read-only audit files are retained under ignored
firmware/dist/validation-run-41067820915 and firmware/dist/rootfs-audit-41067820915.
GitHub artifacts expire 30 days from upload; archive them privately before expiry.
The rootfs report's reviewed_package_source names a temporary local source export
from the exact built revision, not the paused portal worktree. The inspectors
normalize source CRLF only; no image was patched, mounted, executed or flashed.

Independent checks and GitHub image run 41079703855 passed without failures or
warnings. Source CI 41076974981 passed 104 Python/33 JS; portal CI 41076974751
passed 14 tests with actual local HTTP/TLS fixtures. Those identity responses are
fixtures, not real Authelia, WireGuard or controller validation.

programming_authorization=false; hardware_tested=false; production_approved=false.
See ../../HANDOFF-MB00.txt for files, hashes, commissioning and remaining physical
power/capacitor, actual memory/bootloader/backup/recovery and functional tests.
The selected https://connect.atlantisllc.com/u/<serial> label address is not live.
No hosted portal/server deployment is part of this completed offline validation.
