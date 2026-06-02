"""test_sandbox.py — tests for executive/sandbox.py (requires Docker)"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from executive import sandbox

DOCKERFILE_DIR = os.path.join(os.path.dirname(__file__), '..')

def test_build_and_start():
    # Clean up first in case previous run left container
    sandbox.stop()
    time.sleep(1)
    sandbox.start(DOCKERFILE_DIR)
    assert sandbox.is_running(), "Container should be running after start()"
    print("  test_build_and_start: PASS")

def test_run_simple_command():
    stdout, stderr, code = sandbox.run_command("echo HELLO_FROM_CONTAINER")
    assert code == 0, f"exit code {code}"
    assert "HELLO_FROM_CONTAINER" in stdout, f"got: {stdout}"
    print("  test_run_simple_command: PASS")

def test_run_multiline_command():
    stdout, stderr, code = sandbox.run_command("echo LINE1\necho LINE2\necho LINE3")
    assert code == 0, f"exit code {code}"
    assert "LINE1" in stdout
    assert "LINE3" in stdout
    print("  test_run_multiline_command: PASS")

def test_run_command_exit_code():
    stdout, stderr, code = sandbox.run_command("exit 42")
    assert code == 42, f"expected 42, got {code}"
    print("  test_run_command_exit_code: PASS")

def test_run_python_in_container():
    stdout, stderr, code = sandbox.run_command("python3 -c \"print('PYTHON_OK')\"")
    assert code == 0, f"exit code {code}, stderr: {stderr}"
    assert "PYTHON_OK" in stdout
    print("  test_run_python_in_container: PASS")

def test_volume_write_read():
    sandbox.run_command("echo VOLUME_TEST > /mind/volume_test.txt")
    stdout, stderr, code = sandbox.run_command("cat /mind/volume_test.txt")
    assert code == 0, f"exit code {code}"
    assert "VOLUME_TEST" in stdout
    # cleanup
    sandbox.run_command("rm /mind/volume_test.txt")
    print("  test_volume_write_read: PASS")

def test_respawn():
    sandbox.respawn(DOCKERFILE_DIR)
    assert sandbox.is_running(), "Container should be running after respawn"
    stdout, stderr, code = sandbox.run_command("echo AFTER_RESPAWN")
    assert "AFTER_RESPAWN" in stdout
    print("  test_respawn: PASS")

def teardown():
    sandbox.stop()
    print("  [teardown] container stopped")

if __name__ == "__main__":
    print("Running sandbox tests (requires Docker)...")
    try:
        test_build_and_start()
        test_run_simple_command()
        test_run_multiline_command()
        test_run_command_exit_code()
        test_run_python_in_container()
        test_volume_write_read()
        test_respawn()
        print("ALL PASS test_sandbox (7/7)")
    finally:
        teardown()
