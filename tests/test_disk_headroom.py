#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

import ringer


GIB = 1024**3


class DiskHeadroomTests(unittest.TestCase):
    def manifest(self, root: Path, **overrides: object) -> ringer.Manifest:
        obj: dict[str, object] = {
            "run_name": "disk-headroom-test",
            "workdir": str(root / "work"),
            "max_parallel": 2,
            "worktrees": True,
            "repo": str(root / "repo"),
            "tasks": [
                {"key": "one", "spec": "x" * 100, "check": "true"},
                {"key": "two", "spec": "y" * 100, "check": "true"},
            ],
        }
        obj.update(overrides)
        (root / "repo").mkdir(exist_ok=True)
        return ringer.Manifest.from_obj(obj)

    def test_worktree_lfs_defaults_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.assertEqual("materialize", self.manifest(root).worktree_lfs)
            self.assertEqual(
                "skip", self.manifest(root, worktree_lfs="skip").worktree_lfs
            )
            with self.assertRaisesRegex(ValueError, "worktree_lfs"):
                self.manifest(root, worktree_lfs="sometimes")

    def test_projection_uses_repository_size_and_task_count(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest = self.manifest(Path(raw))
            with mock.patch.object(ringer, "repo_checkout_bytes", return_value=7 * GIB):
                self.assertEqual(14 * GIB, ringer.projected_worktree_bytes(manifest))

    def test_low_headroom_blocks_before_workdir_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self.manifest(root)
            usage = ringer.shutil._ntuple_diskusage(400 * GIB, 350 * GIB, 50 * GIB)
            with self.assertRaisesRegex(ringer.DiskPressureError, "below"):
                ringer.preflight_disk_headroom(
                    manifest,
                    disk_usage=usage,
                    projected_bytes=0,
                    pressure_marker=root / "missing-marker",
                    record_block=False,
                )
            self.assertFalse(manifest.workdir.exists())

    def test_projection_and_marker_are_independent_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self.manifest(root)
            usage = ringer.shutil._ntuple_diskusage(400 * GIB, 300 * GIB, 100 * GIB)
            with self.assertRaisesRegex(ringer.DiskPressureError, "projected"):
                ringer.preflight_disk_headroom(
                    manifest,
                    disk_usage=usage,
                    projected_bytes=45 * GIB,
                    pressure_marker=root / "missing-marker",
                    record_block=False,
                )
            marker = root / "DISK_PRESSURE"
            marker.touch()
            with self.assertRaisesRegex(ringer.DiskPressureError, "marker"):
                ringer.preflight_disk_headroom(
                    manifest,
                    disk_usage=usage,
                    projected_bytes=0,
                    pressure_marker=marker,
                    record_block=False,
                )

    def test_sufficient_headroom_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self.manifest(root)
            usage = ringer.shutil._ntuple_diskusage(400 * GIB, 280 * GIB, 120 * GIB)
            receipt = ringer.preflight_disk_headroom(
                manifest,
                disk_usage=usage,
                projected_bytes=20 * GIB,
                pressure_marker=root / "missing-marker",
                record_block=False,
            )
            self.assertEqual(100 * GIB, receipt["remaining_bytes"])

    @unittest.skipUnless(shutil.which("git-lfs"), "git-lfs is not installed")
    def test_worktree_lfs_skip_leaves_pointer_in_real_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            env = {
                **ringer.os.environ,
                "GIT_AUTHOR_NAME": "Ringer Test",
                "GIT_AUTHOR_EMAIL": "ringer-test@example.invalid",
                "GIT_COMMITTER_NAME": "Ringer Test",
                "GIT_COMMITTER_EMAIL": "ringer-test@example.invalid",
            }
            subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
            subprocess.run(["git", "-C", str(repo), "lfs", "install", "--local"], check=True, env=env)
            subprocess.run(["git", "-C", str(repo), "lfs", "track", "*.bin"], check=True, env=env)
            (repo / "media.bin").write_bytes(b"x" * 1024 * 1024)
            subprocess.run(["git", "-C", str(repo), "add", ".gitattributes", "media.bin"], check=True, env=env)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True, env=env)

            manifest = self.manifest(root, repo=str(repo), worktree_lfs="skip")
            engine = ringer.EngineConfig(
                name="mock",
                bin="true",
                args_template=("{spec}",),
                full_access_args=(),
                sandbox_args=(),
            )
            config = ringer.AppConfig(
                path=None,
                identity_default=None,
                state_dir=root / "state",
                dashboard_port_base=8787,
                hud_port=8700,
                hud_app_path=None,
                allow_full_access=False,
                eval=ringer.EvalConfig(backend="jsonl", jsonl_path=root / "eval.jsonl"),
                engines={"mock": engine},
                artifact=ringer.ArtifactConfig(
                    enabled=False,
                    out_template=str(root / "status.html"),
                    report_template=str(root / "report.html"),
                    index_out=root / "index.html",
                ),
            )
            runner = ringer.RingerRunner(
                manifest, config, "test", dashboard_enabled=False
            )
            runtime = runner.runtimes[0]
            prepared, error = asyncio.run(runner._prepare_taskdir(runtime))
            self.assertTrue(prepared, error)
            content = (runtime.taskdir / "media.bin").read_text(encoding="utf-8")
            self.assertIn("git-lfs.github.com/spec/v1", content)
            self.assertLess(len(content), 1024)
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(runtime.taskdir)],
                check=True,
            )


def test_existing_worktree_lfs_defaults_and_validation() -> None:
    DiskHeadroomTests().test_worktree_lfs_defaults_and_validation()


def test_existing_projection_uses_repository_size_and_task_count() -> None:
    DiskHeadroomTests().test_projection_uses_repository_size_and_task_count()


def test_existing_low_headroom_blocks_before_workdir_creation() -> None:
    DiskHeadroomTests().test_low_headroom_blocks_before_workdir_creation()


def test_existing_projection_and_marker_are_independent_blocks() -> None:
    DiskHeadroomTests().test_projection_and_marker_are_independent_blocks()


def test_existing_sufficient_headroom_passes() -> None:
    DiskHeadroomTests().test_sufficient_headroom_passes()


@pytest.mark.skipif(shutil.which("git-lfs") is None, reason="git-lfs is not installed")
def test_existing_worktree_lfs_skip_leaves_pointer_in_real_worktree() -> None:
    DiskHeadroomTests().test_worktree_lfs_skip_leaves_pointer_in_real_worktree()


def test_default_usage_probes_nearest_existing_workdir_ancestor(
    tmp_path: Path,
) -> None:
    manifest = DiskHeadroomTests().manifest(tmp_path)
    calls: list[Path] = []
    usage = ringer.shutil._ntuple_diskusage(500 * GIB, 300 * GIB, 200 * GIB)

    def fake_disk_usage(path: Path) -> shutil._ntuple_diskusage:
        calls.append(Path(path))
        return usage

    with mock.patch.object(ringer.shutil, "disk_usage", side_effect=fake_disk_usage):
        receipt = ringer.preflight_disk_headroom(
            manifest,
            projected_bytes=0,
            pressure_marker=tmp_path / "missing-marker",
            record_block=False,
        )

    assert tmp_path in calls
    assert Path("/") not in calls
    assert receipt["probe_path"] == str(tmp_path)


def test_worktree_repo_with_less_free_space_is_selected(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    repo_root = tmp_path_factory.mktemp("repo-volume")
    repo = repo_root / "repo"
    repo.mkdir()
    manifest = DiskHeadroomTests().manifest(tmp_path, repo=str(repo), worktrees=True)
    workdir_usage = ringer.shutil._ntuple_diskusage(500 * GIB, 300 * GIB, 200 * GIB)
    repo_usage = ringer.shutil._ntuple_diskusage(500 * GIB, 350 * GIB, 150 * GIB)

    def fake_disk_usage(path: Path) -> shutil._ntuple_diskusage:
        return repo_usage if Path(path) == repo else workdir_usage

    with mock.patch.object(ringer.shutil, "disk_usage", side_effect=fake_disk_usage):
        receipt = ringer.preflight_disk_headroom(
            manifest,
            projected_bytes=0,
            pressure_marker=tmp_path / "missing-marker",
            record_block=False,
        )

    assert receipt["probe_path"] == str(repo)
    assert receipt["free_bytes"] == 150 * GIB


def test_injected_usage_reports_injected_probe_path(tmp_path: Path) -> None:
    manifest = DiskHeadroomTests().manifest(tmp_path)
    usage = ringer.shutil._ntuple_diskusage(400 * GIB, 280 * GIB, 120 * GIB)
    receipt = ringer.preflight_disk_headroom(
        manifest,
        disk_usage=usage,
        projected_bytes=20 * GIB,
        pressure_marker=tmp_path / "missing-marker",
        record_block=False,
    )

    assert receipt["probe_path"] == "injected"
    assert receipt["remaining_bytes"] == 100 * GIB


if __name__ == "__main__":
    unittest.main()
