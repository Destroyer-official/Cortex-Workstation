from click.testing import CliRunner
from cortex_unified.cli.cli import main

def test_cli_help():
    """Test that the CLI root command displays help output."""
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'Cortex Workstation' in result.output

def test_cli_version():
    """Test that the CLI version command works."""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_cli_clean_empty_help():
    """Test the help output for the clean-empty subcommand."""
    runner = CliRunner()
    result = runner.invoke(main, ['clean-empty', '--help'])
    assert result.exit_code == 0
    assert 'clean-empty' in result.output.lower()
