import os
import pytest
from click.testing import CliRunner
from pathlib import Path
from reminders.plugins.cli import main


@pytest.fixture
def runner(tmp_path):
    """Create CLI runner with temp work directory"""
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    env = {"REMINDERS_WORK_DIR": str(work_dir), "REMINDERS_MOCK": "1"}
    return CliRunner(env=env), work_dir


def test_cli_add_command(runner):
    """Test reminder add command"""
    cli_runner, work_dir = runner

    result = cli_runner.invoke(main, ['add', 'Call Leon', '--due', '2026-02-14', '--tag', 'phone', '--priority', 'high'])

    assert result.exit_code == 0
    assert "Created OUT-" in result.output
    assert "Call Leon" in result.output

    # Verify file created
    files = list(work_dir.glob("OUT-*.md"))
    assert len(files) == 1


def test_cli_add_with_notes(runner):
    """Test add command with notes"""
    cli_runner, work_dir = runner

    result = cli_runner.invoke(main, ['add', 'Review docs', '--notes', 'Check architecture docs'])

    assert result.exit_code == 0
    assert "Created OUT-" in result.output


def test_cli_list_command(runner):
    """Test reminder list command"""
    cli_runner, work_dir = runner

    # Add tasks first
    cli_runner.invoke(main, ['add', 'Task 1', '--tag', 'test'])
    cli_runner.invoke(main, ['add', 'Task 2', '--tag', 'test'])

    result = cli_runner.invoke(main, ['list'])

    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output
    assert "2 reminders found" in result.output


def test_cli_list_compact_format(runner):
    """Test list with compact output"""
    cli_runner, work_dir = runner

    cli_runner.invoke(main, ['add', 'Task 1'])

    result = cli_runner.invoke(main, ['list', '--format', 'compact'])

    assert result.exit_code == 0
    assert "Task 1" in result.output


def test_cli_list_json_format(runner):
    """Test list with JSON output"""
    cli_runner, work_dir = runner

    cli_runner.invoke(main, ['add', 'Task 1', '--priority', 'high'])

    result = cli_runner.invoke(main, ['list', '--format', 'json'])

    assert result.exit_code == 0
    assert '"title": "Task 1"' in result.output
    assert '"priority": "high"' in result.output


def test_cli_list_empty(runner):
    """Test list with no reminders"""
    cli_runner, work_dir = runner

    result = cli_runner.invoke(main, ['list'])

    assert result.exit_code == 0
    assert "No reminders found" in result.output


def test_cli_list_filter_by_tag(runner):
    """Test list filtered by tag"""
    cli_runner, work_dir = runner

    cli_runner.invoke(main, ['add', 'Task 1', '--tag', 'aussuper'])
    cli_runner.invoke(main, ['add', 'Task 2', '--tag', 'phone'])

    result = cli_runner.invoke(main, ['list', '--tag', 'aussuper'])

    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" not in result.output


def test_cli_complete_command(runner):
    """Test complete command"""
    cli_runner, work_dir = runner

    # Add task
    add_result = cli_runner.invoke(main, ['add', 'Task to complete'])
    # Extract ID from output
    work_item_id = add_result.output.split(":")[0].replace("Created ", "").strip()

    result = cli_runner.invoke(main, ['complete', work_item_id])

    assert result.exit_code == 0
    assert f"Completed {work_item_id}" in result.output


def test_cli_delete_command(runner):
    """Test delete command with --yes flag"""
    cli_runner, work_dir = runner

    add_result = cli_runner.invoke(main, ['add', 'Task to delete'])
    work_item_id = add_result.output.split(":")[0].replace("Created ", "").strip()

    result = cli_runner.invoke(main, ['delete', work_item_id, '--yes'])

    assert result.exit_code == 0
    assert f"Deleted {work_item_id}" in result.output

    # Verify file deleted
    files = list(work_dir.glob("OUT-*.md"))
    assert len(files) == 0


def test_cli_show_command(runner):
    """Test show command"""
    cli_runner, work_dir = runner

    add_result = cli_runner.invoke(main, ['add', 'Task to show', '--priority', 'high', '--tag', 'test'])
    work_item_id = add_result.output.split(":")[0].replace("Created ", "").strip()

    result = cli_runner.invoke(main, ['show', work_item_id])

    assert result.exit_code == 0
    assert "Task to show" in result.output
    assert "Priority: high" in result.output
    assert "test" in result.output


def test_cli_show_not_found(runner):
    """Test show with non-existent ID"""
    cli_runner, work_dir = runner

    result = cli_runner.invoke(main, ['show', 'OUT-999'])

    assert result.exit_code == 1
